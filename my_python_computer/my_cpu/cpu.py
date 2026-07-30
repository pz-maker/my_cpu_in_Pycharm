"""
指令译码器 + ISA 定义（纯组合逻辑）

指令格式（8-bit）：
    [7:4] opcode — 操作码（4-bit，最多 16 条指令）
    [3:2] rd     — 目标寄存器地址（R0~R3）
    [1:0] rs/imm — 源寄存器地址 或 2-bit 立即数
    [3:0] addr   — 跳转地址（M-type 专用，与 rd/rs 复用同一物理位）

指令集真值表：

| opcode | 助记符       | 类型 | 有效字段    | 操作              |
|--------|-------------|------|------------|-------------------|
|  0x0   | NOP         | N    | —          | 空操作            |
|  0x1   | LDI rd,imm  | I    | rd, imm    | rd ← imm (0~3)   |
|  0x2   | MOV rd,rs   | R    | rd, rs     | rd ← rs           |
|  0x3   | ADD rd,rs   | R    | rd, rs     | rd ← rd + rs      |
|  0x4   | SUB rd,rs   | R    | rd, rs     | rd ← rd − rs      |
|  0x5   | LDA rd,rs   | R    | rd, rs     | rd ← mem[rs]      |
|  0x6   | STA rd,rs   | R    | rd, rs     | mem[rs] ← rd      |
|  0x7   | JMP addr    | M    | addr       | PC ← addr         |
|  0x8   | JZ  addr    | M    | addr       | if Z=1: PC ← addr |
|  0x9   | OUT rd      | R    | rd         | port ← rd         |
|  0xF   | HLT         | N    | —          | 停机              |
"""


# ============================================================
#  操作码常量（全大写，§2 命名约定）
# ============================================================
OP_NOP = 0x0
OP_LDI = 0x1
OP_MOV = 0x2
OP_ADD = 0x3
OP_SUB = 0x4
OP_LDA = 0x5
OP_STA = 0x6
OP_JMP = 0x7
OP_JZ  = 0x8
OP_OUT = 0x9
OP_HLT = 0xF

# ============================================================
#  指令类型
# ============================================================
TYPE_N = 0   # 无操作数（NOP, HLT）
TYPE_R = 1   # 寄存器-寄存器（MOV, ADD, SUB, LDA, STA, OUT）
TYPE_I = 2   # 寄存器-立即数（LDI）
TYPE_M = 3   # 地址（JMP, JZ）

# HW: 操作码 → 类型 的映射表，硬件上就是一个 4-to-2 编码器
_OPCODE_TO_TYPE = {
    OP_NOP: TYPE_N,
    OP_LDI: TYPE_I,
    OP_MOV: TYPE_R,
    OP_ADD: TYPE_R,
    OP_SUB: TYPE_R,
    OP_LDA: TYPE_R,
    OP_STA: TYPE_R,
    OP_JMP: TYPE_M,
    OP_JZ:  TYPE_M,
    OP_OUT: TYPE_R,
    OP_HLT: TYPE_N,
}

# HW: 助记符表，仅供 disassemble 调试用，不参与硬件逻辑
_OPCODE_TO_MNEMONIC = {
    OP_NOP: "NOP",
    OP_LDI: "LDI",
    OP_MOV: "MOV",
    OP_ADD: "ADD",
    OP_SUB: "SUB",
    OP_LDA: "LDA",
    OP_STA: "STA",
    OP_JMP: "JMP",
    OP_JZ:  "JZ",
    OP_OUT: "OUT",
    OP_HLT: "HLT",
}


# ============================================================
#  核心译码（纯组合逻辑）
# ============================================================

def decode(instruction: int) -> tuple[int, int, int, int, int]:
    """
    8-bit 指令译码器（纯组合逻辑，无时钟）

    HW: 硬件上就是导线分叉——instruction 的 8 根线
        分别接到 opcode 字段、rd 字段、rs 字段、addr 字段。
        没有任何门电路，纯接线。

    参数：
        instruction : 8-bit 指令字（0~255）

    返回（顺序固定）：
        (opcode, rd, rs, imm, addr)
        - opcode : 4-bit 操作码  [7:4]
        - rd     : 2-bit 目标寄存器 [3:2]
        - rs     : 2-bit 源寄存器   [1:0]
        - imm    : 2-bit 立即数     [1:0]（与 rs 复用同一物理位）
        - addr   : 4-bit 跳转地址   [3:0]（与 rd+rs 复用同一物理位）

    注意：所有字段始终提取，由控制单元根据 opcode 决定哪些有效。
    """
    # HW: 右移 + 掩码 = 硬件上的导线抽取，零延迟
    opcode = (instruction >> 4) & 0x0F   # [7:4]
    rd     = (instruction >> 2) & 0x03   # [3:2]
    rs     = instruction & 0x03          # [1:0]
    imm    = instruction & 0x03          # [1:0]，与 rs 同物理位
    addr   = instruction & 0x0F          # [3:0]
    return (opcode, rd, rs, imm, addr)


def instruction_type(opcode: int) -> int:
    """
    操作码 → 指令类型（纯组合逻辑）

    HW: 4-bit 输入 → 2-bit 输出，本质是一个 4-to-2 编码器。
        控制单元用它决定"该看哪些字段"。

    | opcode       | 返回类型 |
    |-------------|---------|
    | 0x0, 0xF    | TYPE_N  |
    | 0x2~0x6,0x9 | TYPE_R  |
    | 0x1         | TYPE_I  |
    | 0x7, 0x8    | TYPE_M  |
    | 其他（未定义）| TYPE_N  |
    """
    return _OPCODE_TO_TYPE.get(opcode, TYPE_N)


# ============================================================
#  汇编辅助（开发/测试用，非被仿真电路）
# ============================================================

def assemble(opcode: int, rd: int = 0, rs: int = 0,
             imm: int = 0, addr: int = 0) -> int:
    """
    汇编器：助记符参数 → 8-bit 机器码（开发辅助，非硬件）

    根据指令类型自动选择有效字段：

    | 类型   | 编码                          |
    |--------|-------------------------------|
    | TYPE_N | [opcode:4][0000]              |
    | TYPE_R | [opcode:4][rd:2][rs:2]        |
    | TYPE_I | [opcode:4][rd:2][imm:2]       |
    | TYPE_M | [opcode:4][addr:4]            |
    """
    itype = instruction_type(opcode)

    if itype == TYPE_N:
        return (opcode << 4) & 0xFF
    elif itype == TYPE_R:
        return ((opcode << 4) | ((rd & 0x03) << 2) | (rs & 0x03)) & 0xFF
    elif itype == TYPE_I:
        return ((opcode << 4) | ((rd & 0x03) << 2) | (imm & 0x03)) & 0xFF
    elif itype == TYPE_M:
        return ((opcode << 4) | (addr & 0x0F)) & 0xFF

    return (opcode << 4) & 0xFF  # HW: 不可达，防御性兜底


def disassemble(instruction: int) -> str:
    """
    反汇编：8-bit 机器码 → 可读字符串（调试用，非硬件）

    >>> disassemble(0x31)
    'ADD R0, R1'
    >>> disassemble(0x7A)
    'JMP 0xA'
    """
    opcode, rd, rs, imm, addr = decode(instruction)
    mnemonic = _OPCODE_TO_MNEMONIC.get(opcode, f"???({opcode:#04x})")
    itype = instruction_type(opcode)

    if itype == TYPE_N:
        return mnemonic
    elif itype == TYPE_R:
        if opcode == OP_OUT:
            return f"{mnemonic} R{rd}"
        return f"{mnemonic} R{rd}, R{rs}"
    elif itype == TYPE_I:
        return f"{mnemonic} R{rd}, {imm}"
    elif itype == TYPE_M:
        return f"{mnemonic} {addr:#04x}"

    return f"{mnemonic} ???"  # HW: 不可达

# cpu.py
"""
8-bit CPU 顶层：ISA + 译码 + 控制 + 数据通路

指令执行模型（单周期）：
    每个完整时钟周期（tick(0) + tick(1)）执行一条指令。
    clk=0 拍：组合逻辑求值，所有子元件"摆好数据"
    clk=1 拍：触发器捕获，状态更新

数据通路：
    PC → ROM → IR → decode → control → RegFile/ALU/SRAM → write-back
"""

from my_cpu.gates import and_gate, or_gate, not_gate, mux_2to1, mux_4to1, mux_8bit, _bit
from my_cpu.arithmetic import ripple_carry_adder_8bit, alu_8bit, ALU_ADD, ALU_SUB, ALU_PASS_B
from my_cpu.sequential import Register8Bit, ProgramCounter, RegisterFile
from my_cpu.memory import ROM16x8, SRAM16x8

# ============================================================
#  §1  ISA 定义
# ============================================================
OP_NOP = 0x0
OP_LDI = 0x1
OP_MOV = 0x2
OP_ADD = 0x3
OP_SUB = 0x4
OP_LDA = 0x5
OP_STA = 0x6
OP_JMP = 0x7
OP_JZ  = 0x8
OP_OUT = 0x9
OP_HLT = 0xF

TYPE_N = 0
TYPE_R = 1
TYPE_I = 2
TYPE_M = 3

_OPCODE_TO_TYPE = {
    OP_NOP: TYPE_N, OP_LDI: TYPE_I, OP_MOV: TYPE_R,
    OP_ADD: TYPE_R, OP_SUB: TYPE_R, OP_LDA: TYPE_R,
    OP_STA: TYPE_R, OP_JMP: TYPE_M, OP_JZ: TYPE_M,
    OP_OUT: TYPE_R, OP_HLT: TYPE_N,
}

_OPCODE_TO_MNEMONIC = {
    OP_NOP: "NOP", OP_LDI: "LDI", OP_MOV: "MOV",
    OP_ADD: "ADD", OP_SUB: "SUB", OP_LDA: "LDA",
    OP_STA: "STA", OP_JMP: "JMP", OP_JZ: "JZ",
    OP_OUT: "OUT", OP_HLT: "HLT",
}

# ============================================================
#  §2  译码器（纯组合逻辑）
# ============================================================

def decode(instruction: int) -> tuple[int, int, int, int, int]:
    """
    8-bit 指令译码器
    返回 (opcode, rd, rs, imm, addr)，字段始终全提取。
    """
    opcode = (instruction >> 4) & 0x0F
    rd     = (instruction >> 2) & 0x03
    rs     = instruction & 0x03
    imm    = instruction & 0x03
    addr   = instruction & 0x0F
    return (opcode, rd, rs, imm, addr)


def instruction_type(opcode: int) -> int:
    """操作码 → 指令类型"""
    return _OPCODE_TO_TYPE.get(opcode, TYPE_N)


# ============================================================
#  §3  汇编辅助
# ============================================================

def assemble(opcode: int, rd: int = 0, rs: int = 0,
             imm: int = 0, addr: int = 0) -> int:
    """汇编：参数 → 8-bit 机器码"""
    itype = instruction_type(opcode)
    if itype == TYPE_N:
        return (opcode << 4) & 0xFF
    elif itype == TYPE_R:
        return ((opcode << 4) | ((rd & 0x03) << 2) | (rs & 0x03)) & 0xFF
    elif itype == TYPE_I:
        return ((opcode << 4) | ((rd & 0x03) << 2) | (imm & 0x03)) & 0xFF
    elif itype == TYPE_M:
        return ((opcode << 4) | (addr & 0x0F)) & 0xFF
    return (opcode << 4) & 0xFF


def disassemble(instruction: int) -> str:
    """反汇编：机器码 → 可读字符串"""
    opcode, rd, rs, imm, addr = decode(instruction)
    mnemonic = _OPCODE_TO_MNEMONIC.get(opcode, f"???({opcode:#04x})")
    itype = instruction_type(opcode)
    if itype == TYPE_N:
        return mnemonic
    elif itype == TYPE_R:
        if opcode == OP_OUT:
            return f"{mnemonic} R{rd}"
        return f"{mnemonic} R{rd}, R{rs}"
    elif itype == TYPE_I:
        return f"{mnemonic} R{rd}, {imm}"
    elif itype == TYPE_M:
        return f"{mnemonic} {addr:#04x}"
    return f"{mnemonic} ???"


# ============================================================
#  §4  控制单元（纯组合逻辑）
# ============================================================

# 控制信号索引（用元组，顺序固定）
# (reg_wr_en, alu_op, mem_we, pc_load, pc_inc, wb_sel, halt)
#  wb_sel: 0=ALU, 1=reg_b, 2=imm_ext, 3=mem_data
CTL_REG_WR = 0
CTL_ALU_OP = 1
CTL_MEM_WE = 2
CTL_PC_LOAD = 3
CTL_PC_INC = 4
CTL_WB_SEL = 5
CTL_HALT   = 6

def control_unit(opcode: int, z_flag: int) -> tuple[int, int, int, int, int, int, int]:
    """
    控制单元：opcode + z_flag → 7 路控制信号（纯组合逻辑）

    HW: 真实 CPU 的控制单元是一个 PLA（可编程逻辑阵列）——
        输入是 opcode 的 4 根线 + z_flag，输出是各部件的使能/选择线。
        本质上就是一张查找表。

    | opcode | reg_wr | alu_op | mem_we | pc_load | pc_inc | wb_sel | halt |
    |--------|--------|--------|--------|---------|--------|--------|------|
    | NOP    |   0    |   0    |   0    |    0    |   1    |   0    |  0   |
    | LDI    |   1    |   2    |   0    |    0    |   1    |   2    |  0   |
    | MOV    |   1    |   2    |   0    |    0    |   1    |   1    |  0   |
    | ADD    |   1    |   0    |   0    |    0    |   1    |   0    |  0   |
    | SUB    |   1    |   1    |   0    |    0    |   1    |   0    |  0   |
    | LDA    |   1    |   2    |   0    |    0    |   1    |   3    |  0   |
    | STA    |   0    |   2    |   1    |    0    |   1    |   0    |  0   |
    | JMP    |   0    |   2    |   0    |    1    |   0    |   0    |  0   |
    | JZ     |   0    |   2    |   0    |   z     |  ~z    |   0    |  0   |
    | OUT    |   0    |   2    |   0    |    0    |   1    |   0    |  0   |
    | HLT    |   0    |   2    |   0    |    0    |   0    |   0    |  1   |
    """
    # 默认：什么都不做，PC 自增
    reg_wr = 0
    alu_op = ALU_PASS_B
    mem_we = 0
    pc_load = 0
    pc_inc = 1
    wb_sel = 0
    halt = 0

    if opcode == OP_NOP:
        pass  # 默认即可

    elif opcode == OP_LDI:
        reg_wr = 1
        wb_sel = 2       # imm 零扩展

    elif opcode == OP_MOV:
        reg_wr = 1
        wb_sel = 1       # 直通 reg_b

    elif opcode == OP_ADD:
        reg_wr = 1
        alu_op = ALU_ADD
        wb_sel = 0       # ALU 结果

    elif opcode == OP_SUB:
        reg_wr = 1
        alu_op = ALU_SUB
        wb_sel = 0

    elif opcode == OP_LDA:
        reg_wr = 1
        wb_sel = 3       # 内存读数据

    elif opcode == OP_STA:
        mem_we = 1

    elif opcode == OP_JMP:
        pc_load = 1
        pc_inc = 0

    elif opcode == OP_JZ:
        # HW: 条件跳转——pc_load 和 pc_inc 由 z_flag 决定
        pc_load = z_flag
        pc_inc = not_gate(z_flag)

    elif opcode == OP_OUT:
        pass  # 输出端口在 CPU 内部处理

    elif opcode == OP_HLT:
        halt = 1
        pc_inc = 0

    return (reg_wr, alu_op, mem_we, pc_load, pc_inc, wb_sel, halt)


# ============================================================
#  §5  CPU 顶层（数据通路）
# ============================================================

class CPU:
    """
    8-bit 单周期 CPU

    外部接口：
        tick(clk) → None
        一个完整指令周期 = tick(0) + tick(1)

    内部数据通路：
        PC → ROM → IR → decode → control_unit
                                      ↓
                    RegFile ←→ ALU ←→ SRAM
                         ↓
                    write-back mux → RegFile

    两拍协议（§7.1）：
        tick(clk=0)：用上一拍缓存的寄存器值做组合逻辑，
                     计算结果送入各子元件的 data_in（摆数据）
        tick(clk=1)：子元件捕获，更新缓存（出结果）
    """

    def __init__(self, program: list[int]):
        """
        参数：
            program : 最多 16 字节的机器码列表
        """
        # ── 子元件实例化 ──
        self._pc = ProgramCounter()
        self._rom = ROM16x8(program)
        self._ir = Register8Bit()
        self._reg_file = RegisterFile()
        self._sram = SRAM16x8()

        # ── 状态 ──
        self._halted = 0
        self._z_flag = 0
        self._output_port = 0       # OUT 指令的目标
        self._cycle_count = 0

        # ── 缓存：上一拍 clk=1 后各元件的输出 ──
        # HW: 真实硬件中这些是"导线上的电平"，始终可见。
        #     仿真中我们用变量缓存，避免同一相位内重复 tick。
        self._pc_out = 0
        self._reg_outs = [0, 0, 0, 0]

        # ── 暂存：clk=0 算好、clk=1 复用的中间结果 ──
        self._pending = {}

    # ──────────────────────────────────────────────
    #  对外接口
    # ──────────────────────────────────────────────

    def tick(self, clk: int) -> None:
        """
        驱动 CPU 一个时钟相位

        用法（§7.6）：
            cpu.tick(0)   # 摆数据
            cpu.tick(1)   # 出结果
        """
        if self._halted:
            return

        if clk == 0:
            self._phase_evaluate()
        else:
            self._phase_capture()

    def run(self, max_cycles: int = 100) -> None:
        """
        便捷方法：跑完整个程序直到 HLT 或超限

        HW: 这是仿真器层面的循环，不对应任何硬件。
            真实 CPU 只要不断电就一直跑。
        """
        for _ in range(max_cycles):
            if self._halted:
                break
            self.tick(0)
            self.tick(1)

    # ──────────────────────────────────────────────
    #  内部：clk=0 组合逻辑求值
    # ──────────────────────────────────────────────

    def _phase_evaluate(self) -> None:
        """
        clk=0：用缓存值做全部组合逻辑，把结果"摆"到子元件输入端

        求值顺序（§7.4）：
            PC地址 → ROM → 译码 → 控制信号 → 读寄存器 → ALU → 写回选择
        """
        # ① PC → ROM（ROM 是组合逻辑，直接 read）
        pc_addr = self._pc_out
        instruction = self._rom.read(pc_addr)

        # ② 译码
        opcode, rd, rs, imm, addr_field = decode(instruction)

        # ③ 控制信号
        ctrl = control_unit(opcode, self._z_flag)
        reg_wr_en = ctrl[CTL_REG_WR]
        alu_op    = ctrl[CTL_ALU_OP]
        mem_we    = ctrl[CTL_MEM_WE]
        pc_load   = ctrl[CTL_PC_LOAD]
        pc_inc    = ctrl[CTL_PC_INC]
        wb_sel    = ctrl[CTL_WB_SEL]
        halt      = ctrl[CTL_HALT]

        # ④ 读寄存器堆（用缓存值，不 tick）
        reg_a = self._reg_outs[rd & 0x03]   # rd 的值
        reg_b = self._reg_outs[rs & 0x03]   # rs 的值

        # ⑤ ALU
        alu_result, new_z = alu_8bit(alu_op, reg_a, reg_b)

        # ⑥ 内存（SRAM 读出是组合逻辑）
        mem_addr = reg_b & 0x0F             # LDA/STA 用 rs 的值做地址
        mem_data_out = self._sram.read(mem_addr)

        # ⑦ 写回数据选择（4-to-1 mux）
        # HW: 这就是数据通路末端的多路选择器——
        #     决定"这一拍往寄存器里写什么"
        imm_ext = imm & 0x03                # 2-bit 零扩展到 8-bit
        if wb_sel == 0:
            wb_data = alu_result
        elif wb_sel == 1:
            wb_data = reg_b
        elif wb_sel == 2:
            wb_data = imm_ext
        else:  # wb_sel == 3
            wb_data = mem_data_out

        # ⑧ OUT 端口
        if opcode == OP_OUT:
            self._output_port = reg_a

        # ⑨ 暂存所有结果，供 clk=1 复用
        self._pending = {
            'instruction': instruction,
            'opcode': opcode,
            'rd': rd,
            'reg_wr_en': reg_wr_en,
            'wb_data': wb_data,
            'pc_load': pc_load,
            'pc_inc': pc_inc,
            'addr_field': addr_field,
            'mem_we': mem_we,
            'mem_addr': mem_addr,
            'mem_data': reg_a,       # STA 写入的是 rd 的值
            'new_z': new_z,
            'halt': halt,
        }

        # ⑩ 驱动子元件 clk=0（摆数据）
        self._pc.tick(clk=0, rst=0, load=pc_load, inc=pc_inc,
                      data_in=addr_field)
        self._ir.tick(clk=0, data_in=instruction, load=1)
        self._reg_file.tick(clk=0, wr_addr=rd, wr_data=wb_data,
                            wr_en=reg_wr_en, rd_addr_a=rd, rd_addr_b=rs)
        self._sram.tick(clk=0, cs=1, we=mem_we,
                        addr=mem_addr, data_in=reg_a)

    # ──────────────────────────────────────────────
    #  内部：clk=1 捕获
    # ──────────────────────────────────────────────

    def _phase_capture(self) -> None:
        """
        clk=1：子元件捕获，更新缓存

        数据必须与 clk=0 完全一致（§7.2 数据稳定规则）
        """
        p = self._pending

        # PC 更新
        self._pc_out = self._pc.tick(
            clk=1, rst=0, load=p['pc_load'],
            inc=p['pc_inc'], data_in=p['addr_field'])

        # IR 更新（调试可观察）
        self._ir.tick(clk=1, data_in=p['instruction'], load=1)

        # 寄存器堆更新
        data_a, data_b = self._reg_file.tick(
            clk=1, wr_addr=p['rd'], wr_data=p['wb_data'],
            wr_en=p['reg_wr_en'], rd_addr_a=p['rd'], rd_addr_b=0)

        # 更新缓存（HW: 这就是"导线上的新电平"）
        # 需要重新读所有 4 个寄存器的值
        # 但 reg_file.tick 只返回了两个口——我们需要全部 4 个
        # 解决：再 tick 一次？不行，违反原子 tick。
        # HW: 真实硬件中 4 个寄存器的输出线始终可见。
        #     仿真中我们直接访问内部状态（同模块内合理）。
        for i in range(4):
            self._reg_outs[i] = self._reg_file._regs[i]._out

        # SRAM 更新
        self._sram.tick(clk=1, cs=1, we=p['mem_we'],
                        addr=p['mem_addr'], data_in=p['mem_data'])

        # Z flag 更新
        self._z_flag = p['new_z']

        # HLT
        if p['halt']:
            self._halted = 1

        self._cycle_count += 1

    # ──────────────────────────────────────────────
    #  调试接口
    # ──────────────────────────────────────────────

    def dump_state(self) -> str:
        """打印 CPU 当前状态（调试用）"""
        lines = [
            f"--- CPU state (cycle {self._cycle_count}) ---",
            f"  PC  = {self._pc_out:#04x}",
            f"  IR  = {self._ir._out:#04x}  ({disassemble(self._ir._out)})",
            f"  R0  = {self._reg_outs[0]:#04x}  R1 = {self._reg_outs[1]:#04x}",
            f"  R2  = {self._reg_outs[2]:#04x}  R3 = {self._reg_outs[3]:#04x}",
            f"  Z   = {self._z_flag}   OUT = {self._output_port:#04x}",
            f"  Halted = {self._halted}",
        ]
        return "\n".join(lines)