from my_cpu.sequential import ReadAndWriteLatch
from my_cpu.gates import and_gate, decoder_2to4, _bit, and_gate

class MemoryArray4x4:
    """
    4×4 位存储阵列（1-bit 宽，16 个存储位）

    地址结构：addr[3:2] → 行译码器，addr[1:0] → 列译码器

    | addr[3:2] | addr[1:0] | 选中 cell |
    |-----------|-----------|-----------|
    |    00     |    00     |  [0][0]   |
    |    00     |    01     |  [0][1]   |
    |    01     |    10     |  [1][2]   |
    |    11     |    11     |  [3][3]   |
    |   ...     |   ...     |   ...     |

    同一时刻只有 1 个 cell 被选中，其余 15 个保持/Z态。

    接口说明：
    - tick(clk, addr, d_in, we, re) : 时钟驱动，支持读/写/保持
    - read(addr)                    : 异步纯读（组合逻辑），不修改状态
    """

    def __init__(self):
        # 4行 × 4列 = 16 个独立锁存器
        self._cells = [[ReadAndWriteLatch() for _ in range(4)] for _ in range(4)]

    def tick(self, clk: int, addr: int, d_in: int, we: int, re: int) -> int:
        """
        时钟驱动入口（写操作需遵循两拍协议）

        | we | re | 操作           | 返回值         |
        |----|----|---------------|----------------|
        | 0  | 0  | 保持           | -1 (Z)         |
        | 0  | 1  | 读             | cell 当前值    |
        | 1  | 0  | 写（不输出）    | -1 (Z)         |
        | 1  | 1  | 写+读回        | 写入后的新值   |
        """
        # === 组合逻辑：4根地址线 → 2个译码器 ===
        # HW: addr 物理上是4根导线，直接按位接
        row_sel = decoder_2to4(_bit(addr, 2), _bit(addr, 3))
        col_sel = decoder_2to4(_bit(addr, 0), _bit(addr, 1))

        # === 逐 cell 驱动 ===
        result = -1
        for r in range(4):
            for c in range(4):
                selected = and_gate(row_sel[r], col_sel[c])
                cell_we = and_gate(we, selected)
                cell_re = and_gate(re, selected)

                out = self._cells[r][c].update(d_in, cell_we, cell_re)

                if cell_re == 1:
                    result = out

        return result

    def read(self, addr: int) -> int:
        """
        异步读出（纯组合逻辑，不依赖 clk，不修改任何 cell 状态）

        HW: 真实 SRAM 的读通路是异步的——地址有效 + 片选有效 → 数据立即输出。
            此方法模拟该行为：we=0 保证不写入，re=1 打开输出三态门。
            供 SRAM16x8 的读出通路调用。

        参数：
            addr : 4-bit 地址（0~15）
        返回：
            选中 cell 的当前存储值（0 或 1）
        """
        row_sel = decoder_2to4(_bit(addr, 2), _bit(addr, 3))
        col_sel = decoder_2to4(_bit(addr, 0), _bit(addr, 1))

        for r in range(4):
            for c in range(4):
                selected = and_gate(row_sel[r], col_sel[c])
                if selected == 1:
                    # HW: d_in=0 是 don't care（we=0 时不采样），re=1 打开输出
                    return self._cells[r][c].update(0, 0, 1)

        return -1  # HW: 理论上不可达，4-bit 地址必中一个 cell

# memory.py

from my_cpu.gates import split_bus_8bit, collect_bus_8bit, _bit, and_gate, decoder_2to4

class SRAM16x8:
    """
    8-bit 宽 × 16 字 SRAM（由 8 个 MemoryArray4x4 位切片并联构成）

    地址空间：16 个字（addr 4-bit），每字 8-bit

    状态表：

    | cs | we | 操作         | data_out       |
    |----|----|-------------|----------------|
    | 0  | X  | 高阻（不选中）| -1 (Z)         |
    | 1  | 0  | 读           | mem[addr]      |
    | 1  | 1  | 写（两拍）    | mem[addr](新值) |

    内部结构（位切片并联）：
        data_in ──→ [split_bus_8bit] ──→ b0 ──→ slice[0]
                                       ──→ b1 ──→ slice[1]
                                       ...
                                       ──→ b7 ──→ slice[7]

        slice[0].read() ──→ out0 ─┐
        slice[1].read() ──→ out1 ─┤
        ...                       ├──→ [collect_bus_8bit] ──→ data_out
        slice[7].read() ──→ out7 ─┘
    """

    NUM_WORDS = 16
    DATA_WIDTH = 8

    def __init__(self):
        # HW: 8 个 1-bit 宽的 4×4 阵列并联，构成 8-bit 数据通路
        #     物理上等价于 SRAM 芯片内部的 bit-line 扩展
        self._slices = [MemoryArray4x4() for _ in range(self.DATA_WIDTH)]

    def read(self, addr: int) -> int:
        """
        异步读出（纯组合逻辑，不需要时钟）

        HW: 真实 SRAM 的读路径不经过时钟——
            地址线有效 → 各切片同时输出对应位 → 收线器拼回 8-bit。
            只有"写"才需要时钟沿。

        参数：
            addr : 4-bit 地址（0~15）
        返回：
            8-bit 数据
        """
        masked_addr = addr & 0x0F
        bits_out = tuple(
            self._slices[bit_idx].read(masked_addr)
            for bit_idx in range(self.DATA_WIDTH)
        )
        return collect_bus_8bit(*bits_out)

    def tick(self, clk: int, cs: int, we: int, addr: int, data_in: int) -> int:
        """
        时钟驱动入口（写操作遵循两拍协议）

        参数：
            clk     : 时钟，0=低电平（摆数据），1=高电平（出结果）
            cs      : 片选，1=选中，0=高阻
            we      : 写使能，1=写，0=读
            addr    : 4-bit 地址（0~15）
            data_in : 8-bit 写入数据（仅 we=1 时有效）

        返回：
            8-bit 读出数据；cs=0 时返回 -1（高阻态 Z）
        """
        # HW: 片选无效时，数据总线呈高阻，模拟三态门断开
        if cs == 0:
            return -1

        # ── 写入通路：分线器拆总线 → 逐位喂入各切片 ──
        # HW: split_bus_8bit 就是原理图上总线末端的扇形展开符号
        #     返回 (b0, b1, ..., b7)，低位在前，与切片索引一一对应
        bits_in = split_bus_8bit(data_in)

        for bit_idx in range(self.DATA_WIDTH):
            self._slices[bit_idx].tick(
                clk=clk,
                addr=addr,
                d_in=bits_in[bit_idx],  # 第 i 个切片只看到第 i 根线
                we=we,
                re=0                    # HW: 写操作时关闭读输出，避免总线冲突
            )

        # ── 读出通路：各切片异步读 → 收线器拼回总线 ──
        # HW: collect_bus_8bit 就是原理图上 8 根线汇入总线的扇形收束符号
        #     参数顺序 (b0, b1, ..., b7) 与 split 返回顺序一致，直接对接
        bits_out = tuple(
            self._slices[bit_idx].read(addr)
            for bit_idx in range(self.DATA_WIDTH)
        )  # (out0, out1, ..., out7)

        data_out = collect_bus_8bit(*bits_out)

        return data_out

class ROM16x8:
    """
    8-bit 宽 × 16 字 ROM（只读存储器 / 指令存储器）

    HW: 真实 ROM 是二极管矩阵或熔丝阵列——地址译码选中一行，
        该行上"有二极管"的位输出1，"没有"的输出0。
        程序在制造时就固定了，运行时不可改写。
        本模型用不可变元组模拟"烧死"语义。

    地址空间：16 个字（addr 4-bit），每字 8-bit

    状态表（纯组合逻辑，无时钟）：

    | addr (0~15) | data_out        |
    |-------------|-----------------|
    |      0      | program[0]      |
    |      1      | program[1]      |
    |     ...     | ...             |
    |     15      | program[15]     |

    与 SRAM16x8 的关键区别：
    - 无 clk / cs / we —— 地址有效即输出，永远只读
    - 无 tick() —— 不是时序元件，是组合逻辑
    - 内容不可变 —— 构造后无法修改（tuple 保证）
    """

    NUM_WORDS = 16
    DATA_WIDTH = 8

    def __init__(self, program: list[int]):
        """
        "烧录"程序（等价于工厂掩膜）

        参数：
            program : 最多 16 个字节（0~255），不足 16 字自动补 0x00
                      超出 16 字截断（硬件地址线只有 4 根，高位丢弃）

        HW: 真实 ROM 的"写入"发生在制造阶段（离子注入/熔丝烧断），
            之后内容永久固定。这里用 tuple 的不可变性模拟该约束。
        """
        # HW: 截断到 16 字，不足补 0x00（相当于空白 ROM 全为 0）
        padded = list(program[:self.NUM_WORDS])
        padded += [0x00] * (self.NUM_WORDS - len(padded))

        # HW: 转为 tuple → 任何 self._data[x] = y 都会抛 TypeError
        #     这就是"只读"的软件等价物
        self._data = tuple(padded)

    def read(self, addr: int) -> int:
        """
        异步读出（纯组合逻辑）

        HW: 地址线有效 → 译码器选中一行 → 数据立即出现在输出端。
            没有时钟沿、没有使能信号——只要地址稳定，输出就稳定。
            这就是为什么 PC 一变，指令立刻出现在 IR 输入端。

        参数：
            addr : 4-bit 地址（0~15），超出范围自动截断低 4 位
        返回：
            8-bit 指令字（0~255）
        """
        # HW: 物理上只有 4 根地址线，高位根本接不上，自然丢弃
        masked_addr = addr & 0x0F
        return self._data[masked_addr]