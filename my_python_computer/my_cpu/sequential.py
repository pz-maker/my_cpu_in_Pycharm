from my_cpu.gates import nand_gate, not_gate

class SRLatch:
    """
    SR 锁存器（NAND 实现，低电平有效）

    状态表：

    | S | R | Q_next | 说明       |
    |---|---|--------|------------|
    | 0 | 1 |   1    | Set 置位   |
    | 1 | 0 |   0    | Reset 复位 |
    | 1 | 1 |  不变  | Hold 保持  |
    | 0 | 0 |  禁止  | Q=Q̄=1     |

    初始状态：Q=0, Q̄=1
    """

    def __init__(self):
        # HW: 上电默认状态，Q=0 表示锁存器未存储有效数据
        self._q = 0
        # HW: Q̄ 是 Q 的逻辑反，初始必须与 Q 互补，故 Q̄=1
        self._q_bar = 1

    def update(self, s: int, r: int) -> tuple[int, int]:
        """
        更新锁存器状态并返回稳态 (Q, Q̄)
        s: Set 输入端，低电平有效（0=激活Set）
        r: Reset 输入端，低电平有效（0=激活Reset）
        """
        # HW: 真实硬件中两个NAND门并行计算、经传播延迟后收敛到稳态；
        #     仿真无法真正并行，故用迭代逼近模拟该物理过程。
        #     2门交叉耦合最多2~3轮即收敛，10轮为安全上限。
        for _ in range(10):
            # HW: 计算NAND门1的输出，即Q的新候选值。
            #     s=0时：NAND(0,任意)=1，强制Q=1 → Set生效；
            #     s=1时：NAND(1,Q̄)=NOT(Q̄)，Q由反馈决定 → Hold。
            #     此处self._q_bar是上一轮的旧值，模拟门1看到门2的旧输出。
            new_q = nand_gate(s, self._q_bar)

            # HW: 计算NAND门2的输出，即Q̄的新候选值。
            #     r=0时：NAND(0,任意)=1，强制Q̄=1 → Reset生效（Q被拉低）；
            #     r=1时：NAND(1,Q)=NOT(Q)，Q̄由反馈决定 → Hold。
            #     此处self._q仍是本轮开始时的旧值，保证两门同时基于旧状态计算。
            new_q_bar = nand_gate(r, self._q)

            # HW: 新旧值完全一致 → 电路已达稳态，再迭代也不会变化。
            if new_q == self._q and new_q_bar == self._q_bar:
                # HW: 提前退出循环，避免无意义的重复计算。
                break

            # HW: 尚未收敛，将新值写回作为下一轮的"旧值"。
            #     等效于信号又经过了一个门延迟的传播。
            self._q = new_q
            # HW: 同步更新Q̄，保持两轮迭代之间状态的一致性。
            self._q_bar = new_q_bar

        # HW: 返回最终稳态结果，元组顺序固定为(Q, Q̄)。
        return self._q, self._q_bar

    @property
    def q(self) -> int:
        # HW: 只读属性，防止外部代码直接篡改锁存器内部状态。
        return self._q

    @property
    def q_bar(self) -> int:
        # HW: 只读属性，防止外部代码直接篡改锁存器内部状态。
        return self._q_bar


class GatedDLatch:
    """
    门控D锁存器（电平敏感）

    | en | d | q (next) | 说明           |
    |----|---|----------|----------------|
    |  0 | X | q (hold) | 使能关闭，保持 |
    |  1 | 0 |    0     | 使能打开，透传 |
    |  1 | 1 |    1     | 使能打开，透传 |

    HW: 内部结构 = 输入转换逻辑 + SR Latch
        输入转换逻辑将 (d, en) 转换为 SR Latch 的 (s_bar, r_bar)，
        确保 en=0 时 s_bar=r_bar=1（保持），en=1 时 s_bar/r_bar 由 d 决定。
    """
    def __init__(self):
        # HW: 内部包含一个SR Latch作为存储核心
        self._sr_latch = SRLatch()

    def update(self, en: int, d: int) -> int:
        """
        更新门控D锁存器。
        Args:
            en: 使能信号 (0/1)，高电平时透明
            d:  数据输入 (0/1)
        Returns:
            当前 Q 输出 (0/1)
        """

        not_d = not_gate(d)

        s_bar = nand_gate(en, d)

        r_bar = nand_gate(en, not_d)

        # === 驱动内部 SR Latch ===
        q, _ = self._sr_latch.update(s_bar, r_bar)
        return q


class DFlipFlop:
    """
    主从D触发器（上升沿触发）

    状态转移表：

    | clk       | d   | q (next) | 说明             |
    |-----------|-----|----------|------------------|
    | 0         | X   | q (hold) | 低电平，保持     |
    | 1→0 (↓)   | X   | q (hold) | 下降沿，保持     |
    | 0→1 (↑)   | 0   |    0     | 上升沿，采样 d=0 |
    | 0→1 (↑)   | 1   |    1     | 上升沿，采样 d=1 |

    HW: 物理结构 = Master(GatedDLatch) + NOT(clk) + Slave(GatedDLatch)
        Master 在 clk=0 时透明（采样D），clk=1 时锁存；
        Slave  在 clk=1 时透明（传递Q_m），clk=0 时锁存。
        两者互斥工作，将"电平窗口"压缩为"上升沿瞬间"。
    """
    def __init__(self):
        # HW: Master 锁存器 —— 负责在 clk=0 期间"吸气"采样 D
        self._master = GatedDLatch()
        # HW: Slave 锁存器 —— 负责在 clk=1 期间"呼气"输出 Q
        self._slave = GatedDLatch()
        # HW: 记录上一拍时钟值，用于在仿真中检测上升沿
        #     真实电路靠物理延迟自然实现边沿检测，
        #     但Python是离散步进仿真，必须显式记住"上一次clk是多少"
        self._prev_clk = 0

    def tick(self, clk: int, d: int) -> int:
        """
        时钟驱动入口。仅在上升沿采样d，其余时刻保持。

        Args:
            clk: 时钟信号 (0/1)
            d:   数据输入 (0/1)
        Returns:
            当前 Q 输出 (0/1)
        """
        # ============================================================
        # HW: 关键！这里模拟的是"一个时钟步长内信号的传播过程"
        #     在真实电路中，Master和Slave是同时工作的物理器件，
        #     但在Python仿真中，我们必须按因果顺序依次计算：
        #     先算Master的输出 → 再算Slave的输出
        # ============================================================

        # HW: 生成 clk_bar（反相时钟）
        #     这就是连接Master和Slave的那根反相导线
        clk_bar = not_gate(clk)

        # HW: Master 的使能 = clk_bar
        #     clk=0 → clk_bar=1 → Master透明，咬住D
        #     clk=1 → clk_bar=0 → Master锁存，守住之前的值
        q_master = self._master.update(en=clk_bar, d=d)

        # HW: Slave 的使能 = clk
        #     clk=1 → Slave透明，把Q_m传递到Q
        #     clk=0 → Slave锁存，保住当前Q
        # HW: Slave 的数据输入 = Master 的输出 q_master
        #     这就是两个Latch之间那根内部连线
        q_out = self._slave.update(en=clk, d=q_master)

        # HW: 更新 prev_clk，供下一次 tick 调用时使用
        self._prev_clk = clk

        return q_out


# ============================================================
#  sequential.py（追加部分）
#  新增：Register8Bit —— 8-bit 并行加载寄存器
# ============================================================

# ─── 导入旧元件 ───
#
# from 模块名 import 名字1, 名字2, ...
#   意思：从那个 .py 文件里，把指定的函数/类"拿过来"用
#
# mux_2to1(sel, in0, in1)
#   sel=0 → 返回 in0
#   sel=1 → 返回 in1
#
# split_bus_8bit(value)
#   把一个 0~255 的整数拆成 8 个 0/1 的元组
#   例：split_bus_8bit(0b10110001) → (1,0,0,0,1,1,0,1)
#
# collect_bus_8bit(b0,b1,b2,b3,b4,b5,b6,b7)
#   把 8 个 0/1 拼回一个整数
#   例：collect_bus_8bit(1,0,0,0,1,1,0,1) → 177
#
from my_cpu.gates import mux_2to1, split_bus_8bit, collect_bus_8bit

class Register8Bit:
    """
    8-bit 并行加载寄存器

    真值表:

    | clk↑ | load | data_in | 动作     | out  |
    |------|------|---------|----------|------|
    |  1   |  0   |   X     | 保持     | 旧值 |
    |  1   |  1   |   D     | 加载     | D    |
    |  0   |  X   |   X     | 无沿保持 | 旧值 |

    HW: 8个DFlipFlop各存1bit；
        每位前面一个mux_2to1，sel=load；
        load=0 → mux输出反馈（保持）；
        load=1 → mux输出新数据（加载）。
    """


    BIT_WIDTH = 8


    def __init__(self):
        """创建 8 个触发器 + 1 个输出缓存"""


        self._ffs = tuple(DFlipFlop() for _ in range(self.BIT_WIDTH))


        self._out = 0


    def tick(self, clk: int, data_in: int, load: int) -> int:
        """
        每个时钟周期调用一次。

        参数:
            clk     : 时钟，0 或 1
            data_in : 要写入的 8-bit 数据（0~255 的整数）
            load    : 1=加载新数据，0=保持旧值

        返回:
            当前寄存器输出（0~255 的整数）
        """


        bits = split_bus_8bit(data_in)


        out_bits = []


        for i in range(self.BIT_WIDTH):


            feedback = (self._out >> i) & 1

            # ── 2b. mux 选择 ──
            #
            # mux_2to1(sel, in0, in1)
            #   sel=0 → 返回 in0
            #   sel=1 → 返回 in1
            #
            # 我们这样接：
            #   sel  = load        （外部控制信号）
            #   in0  = feedback    （保持端：自己的旧值）
            #   in1  = bits[i]     （加载端：外部新数据）
            #
            # 所以：
            #   load=0 → d = feedback → FF 锁存自己的旧值 → 保持
            #   load=1 → d = bits[i]  → FF 锁存外部数据   → 加载
            #
            # HW: 每位 FF 前面的 2 选 1 多路选择器
            #
            d = mux_2to1(load, feedback, bits[i])

            # ── 2c. 驱动触发器 ──
            #
            # 铁律：每个 FF 每个时钟周期只能 tick 一次！
            #
            # FF 内部自己判断：
            #   上一拍 clk=0，这一拍 clk=1 → 上升沿 → 锁存 d
            #   其他情况                   → 保持原值
            #
            # 返回值 q 就是 FF 当前的输出（0 或 1）
            #
            q = self._ffs[i].tick(clk, d)

            # ── 2d. 收集本位输出 ──
            #
            # .append(东西)  →  在列表末尾追加一个元素
            #
            # 循环 8 次后：
            #   out_bits = [q0, q1, q2, q3, q4, q5, q6, q7]
            #
            out_bits.append(q)

        # ══════════════════════════════════════════════
        #  第 3 步：合线
        #  把 8 根独立导线 → 1 根 8-bit 总线
        # ══════════════════════════════════════════════
        #
        # collect_bus_8bit(b0, b1, b2, b3, b4, b5, b6, b7)
        #   需要 8 个独立参数
        #
        # 但 out_bits 是一个列表 [q0, q1, ..., q7]
        # 怎么把列表"展开"成 8 个独立参数？
        #
        # 用 * 号（解包）：
        #   collect_bus_8bit(*out_bits)
        #   等价于
        #   collect_bus_8bit(q0, q1, q2, q3, q4, q5, q6, q7)
        #
        # * 的作用：把列表/元组"拆散"成一个个独立参数
        #
        self._out = collect_bus_8bit(*out_bits)

        # ══════════════════════════════════════════════
        #  第 4 步：返回
        # ══════════════════════════════════════════════
        #
        # 返回当前寄存器值（整数，0~255）
        # 同时 self._out 已更新，下一拍的 feedback 会用到它
        #
        return self._out

from my_cpu.gates import mux_8bit
from my_cpu.arithmetic import ripple_carry_adder_8bit
# ─────────────────────────────────────────────
# ProgramCounter
# ─────────────────────────────────────────────

class ProgramCounter:
    """
    8-bit 程序计数器（PC）

    功能：存储下一条指令的地址，支持复位 / 跳转 / 自增 / 保持。

    控制优先级（高 → 低）：rst > load > inc > hold

    状态转移表：

    | 当前Q | rst | load | inc | 下一状态 Q'        | 语义     |
    |-------|-----|------|-----|------------------|----------|
    | 任意  |  1  |  x   |  x  | 0x00             | 复位     |
    |  Q    |  0  |  1   |  x  | data_in & 0xFF   | 跳转     |
    |  Q    |  0  |  0   |  1  | (Q + 1) & 0xFF   | 顺序取指 |
    |  Q    |  0  |  0   |  0  | Q                | 保持     |

    时序：遵循两拍协议（§7.1）
        tick(clk=0, ...) → 摆数据
        tick(clk=1, ...) → 出结果
    """

    def __init__(self) -> None:
        self._reg = Register8Bit()   # 内部寄存器，外部不可访问
        self._current: int = 0       # 缓存当前输出（= 寄存器 Q 端）

    def tick(self, clk: int, rst: int, load: int, inc: int, data_in: int) -> int:
        """
        时钟驱动入口。

        参数：
            clk     : 0 或 1（时钟相位）
            rst     : 0 或 1（异步复位，优先级最高）
            load    : 0 或 1（并行加载 / 跳转）
            inc     : 0 或 1（自增）
            data_in : 0~255（跳转目标地址）

        返回：
            int, 0~255（当前 PC 值）
        """
        # ── ① 组合逻辑：计算 PC+1 ──
        # HW: 加法器只认 _current 和常数 1，data_in 不参与运算
        plus_one, _ = ripple_carry_adder_8bit(self._current, 1, cin=0)

        # ── ② 组合逻辑：三级 mux 优先级选择链 ──
        # HW: 优先级从低到高排列，高优先级 mux 在最后（靠近寄存器）
        #     这样高优先级信号能"覆盖"低优先级的选择结果
        level1 = mux_8bit(inc, self._current, plus_one)  # hold vs +1
        level2 = mux_8bit(load, level1, data_in & 0xFF)  # ↑   vs jump
        level3 = mux_8bit(rst, level2, 0x00)  # ↑   vs reset

        # ── ③ 时序元件：写入寄存器 ──
        # HW: load 引脚恒为 1，"是否更新"的决策已被 mux 链吸收
        #     寄存器每拍都写入 final_val，但值可能是旧值（hold 时）
        self._current = self._reg.tick(clk, data_in=level3, load=1)

        return self._current


#锁存器，可读，可写,同样手搓
from my_cpu.gates import tristate_buf

class ReadAndWriteLatch:
    def __init__(self):
        self._GatedDLatch = GatedDLatch()
        self._read = tristate_buf

    def update(self, data_in: int, write: int, read: int) -> int:
        q = self._GatedDLatch.update(write, data_in)
        q_read = self._read(q, read)
        return q_read


# sequential.py 末尾追加
from my_cpu.gates import and_gate
class RegisterFile:
    """
    4×8-bit 寄存器堆（双读口、单写口）

    HW: 真实 CPU 的寄存器堆是一个小型 RAM——
        地址译码选中一行（寄存器），位线读出/写入。
        两个读口 = 两组位线，互不干扰。
        写口只有一个（单周期 CPU 每拍最多写一个寄存器）。

    接口：
        tick(clk, wr_addr, wr_data, wr_en, rd_addr_a, rd_addr_b)
            → (data_a, data_b)

    状态表：

    | clk | wr_en | 行为                              |
    |-----|-------|-----------------------------------|
    |  0  |   x   | 主锁存器透明，捕获 wr_data（摆数据）|
    |  1  |   0   | 所有寄存器保持，读出当前值          |
    |  1  |   1   | wr_addr 对应寄存器更新，其余保持    |

    读口是纯组合逻辑（任何时候都能读），写口受时钟控制。
    """

    NUM_REGS = 4
    REG_WIDTH = 8

    def __init__(self):
        # HW: 4 个独立的 8-bit 寄存器，物理上是 4 行触发器阵列
        self._regs = [Register8Bit() for _ in range(self.NUM_REGS)]

    def tick(self, clk: int, wr_addr: int, wr_data: int,
             wr_en: int, rd_addr_a: int, rd_addr_b: int) -> tuple[int, int]:
        """
        单拍驱动整个寄存器堆（原子 tick，§7.3）

        参数：
            clk       : 时钟相位（0=摆数据，1=出结果）
            wr_addr   : 写地址（0~3），仅 wr_en=1 时有效
            wr_data   : 写入数据（8-bit）
            wr_en     : 写使能（0=全保持，1=写 wr_addr）
            rd_addr_a : 读口 A 地址（0~3）→ 通常接 rd
            rd_addr_b : 读口 B 地址（0~3）→ 通常接 rs

        返回：
            (data_a, data_b) — 两个读口的当前值
        """
        # HW: 逐寄存器 tick，只有地址匹配且 wr_en=1 的那个才 load=1
        #     其余 load=0 → 保持。这模拟了地址译码器的 one-hot 输出。
        outputs = []
        for i, reg in enumerate(self._regs):
            load = and_gate(
                1 if i == (wr_addr & 0x03) else 0,
                wr_en
            )
            val = reg.tick(clk, data_in=wr_data, load=load)
            outputs.append(val)

        # HW: 读口是组合逻辑——直接从触发器输出端接线，不经过时钟
        data_a = outputs[rd_addr_a & 0x03]
        data_b = outputs[rd_addr_b & 0x03]
        return (data_a, data_b)


