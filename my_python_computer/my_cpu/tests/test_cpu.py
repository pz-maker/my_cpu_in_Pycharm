import pytest
from my_cpu.cpu import (
    decode, instruction_type, assemble, disassemble,
    OP_NOP, OP_LDI, OP_MOV, OP_ADD, OP_SUB,
    OP_LDA, OP_STA, OP_JMP, OP_JZ, OP_OUT, OP_HLT,
    TYPE_N, TYPE_R, TYPE_I, TYPE_M,
)


class TestDecode:
    """decode() 穷举 + 定向测试"""

    # ── 穷举：所有 256 条指令字 ──

    def test_exhaustive_256(self):
        """遍历 0x00~0xFF，验证字段提取的数学正确性"""
        for instr in range(256):
            opcode, rd, rs, imm, addr = decode(instr)
            assert opcode == (instr >> 4) & 0x0F
            assert rd     == (instr >> 2) & 0x03
            assert rs     == instr & 0x03
            assert imm    == instr & 0x03
            assert addr   == instr & 0x0F

    def test_return_is_5_tuple_of_int(self):
        """返回值是 5 元组，全为 int"""
        result = decode(0x00)
        assert isinstance(result, tuple)
        assert len(result) == 5
        assert all(isinstance(v, int) for v in result)

    # ── 定向：每条指令各测一条 ──

    def test_nop(self):
        assert decode(0x00) == (OP_NOP, 0, 0, 0, 0)

    def test_hlt(self):
        assert decode(0xF0) == (OP_HLT, 0, 0, 0, 0)

    def test_ldi_r2_imm3(self):
        # LDI R2, 3 → 0001_10_11 = 0x1B
        opcode, rd, rs, imm, addr = decode(0x1B)
        assert opcode == OP_LDI
        assert rd == 2
        assert imm == 3

    def test_add_r1_r3(self):
        # ADD R1, R3 → 0011_01_11 = 0x37
        opcode, rd, rs, imm, addr = decode(0x37)
        assert opcode == OP_ADD
        assert rd == 1
        assert rs == 3

    def test_sub_r3_r0(self):
        # SUB R3, R0 → 0100_11_00 = 0x4C
        opcode, rd, rs, _, _ = decode(0x4C)
        assert opcode == OP_SUB
        assert rd == 3
        assert rs == 0

    def test_mov_r0_r2(self):
        # MOV R0, R2 → 0010_00_10 = 0x22
        opcode, rd, rs, _, _ = decode(0x22)
        assert opcode == OP_MOV
        assert rd == 0
        assert rs == 2

    def test_lda_r1_r2(self):
        # LDA R1, R2 → 0101_01_10 = 0x56
        opcode, rd, rs, _, _ = decode(0x56)
        assert opcode == OP_LDA
        assert rd == 1
        assert rs == 2

    def test_sta_r3_r1(self):
        # STA R3, R1 → 0110_11_01 = 0x6D
        opcode, rd, rs, _, _ = decode(0x6D)
        assert opcode == OP_STA
        assert rd == 3
        assert rs == 1

    def test_jmp_addr_10(self):
        # JMP 0xA → 0111_1010 = 0x7A
        opcode, _, _, _, addr = decode(0x7A)
        assert opcode == OP_JMP
        assert addr == 0x0A

    def test_jz_addr_5(self):
        # JZ 0x5 → 1000_0101 = 0x85
        opcode, _, _, _, addr = decode(0x85)
        assert opcode == OP_JZ
        assert addr == 0x05

    def test_out_r2(self):
        # OUT R2 → 1001_10_00 = 0x98
        opcode, rd, _, _, _ = decode(0x98)
        assert opcode == OP_OUT
        assert rd == 2

    # ── rs 与 imm 复用同一物理位 ──

    def test_rs_imm_same_bits(self):
        """rs 和 imm 始终相等（同一根线）"""
        for instr in range(256):
            _, _, rs, imm, _ = decode(instr)
            assert rs == imm


class TestInstructionType:
    """instruction_type() 分类测试"""

    @pytest.mark.parametrize("opcode,expected", [
        (OP_NOP, TYPE_N),
        (OP_HLT, TYPE_N),
        (OP_LDI, TYPE_I),
        (OP_MOV, TYPE_R),
        (OP_ADD, TYPE_R),
        (OP_SUB, TYPE_R),
        (OP_LDA, TYPE_R),
        (OP_STA, TYPE_R),
        (OP_OUT, TYPE_R),
        (OP_JMP, TYPE_M),
        (OP_JZ,  TYPE_M),
    ])
    def test_known_opcodes(self, opcode, expected):
        assert instruction_type(opcode) == expected

    def test_undefined_opcode_defaults_to_n(self):
        """未定义操作码（0xA~0xE）回退到 TYPE_N"""
        for op in [0xA, 0xB, 0xC, 0xD, 0xE]:
            assert instruction_type(op) == TYPE_N


class TestAssemble:
    """assemble() 编码测试"""

    def test_nop(self):
        assert assemble(OP_NOP) == 0x00

    def test_hlt(self):
        assert assemble(OP_HLT) == 0xF0

    def test_ldi_r2_imm3(self):
        assert assemble(OP_LDI, rd=2, imm=3) == 0x1B

    def test_add_r1_r3(self):
        assert assemble(OP_ADD, rd=1, rs=3) == 0x37

    def test_jmp_addr_10(self):
        assert assemble(OP_JMP, addr=0x0A) == 0x7A

    def test_jz_addr_5(self):
        assert assemble(OP_JZ, addr=0x05) == 0x85

    def test_out_r2(self):
        assert assemble(OP_OUT, rd=2) == 0x98

    def test_field_masking(self):
        """超出范围的参数被掩码截断"""
        # rd=7 → 7 & 0x03 = 3
        assert assemble(OP_MOV, rd=7, rs=0) == assemble(OP_MOV, rd=3, rs=0)
        # addr=0xFF → 0xFF & 0x0F = 0x0F
        assert assemble(OP_JMP, addr=0xFF) == assemble(OP_JMP, addr=0x0F)


class TestAssembleDecodeRoundtrip:
    """assemble → decode 往返一致性（穷举所有合法指令）"""

    def test_roundtrip_n_type(self):
        for op in [OP_NOP, OP_HLT]:
            instr = assemble(op)
            opcode, _, _, _, _ = decode(instr)
            assert opcode == op

    def test_roundtrip_r_type(self):
        for op in [OP_MOV, OP_ADD, OP_SUB, OP_LDA, OP_STA]:
            for rd in range(4):
                for rs in range(4):
                    instr = assemble(op, rd=rd, rs=rs)
                    opcode, d_rd, d_rs, _, _ = decode(instr)
                    assert opcode == op
                    assert d_rd == rd
                    assert d_rs == rs

    def test_roundtrip_i_type(self):
        for rd in range(4):
            for imm in range(4):
                instr = assemble(OP_LDI, rd=rd, imm=imm)
                opcode, d_rd, _, d_imm, _ = decode(instr)
                assert opcode == OP_LDI
                assert d_rd == rd
                assert d_imm == imm

    def test_roundtrip_m_type(self):
        for op in [OP_JMP, OP_JZ]:
            for addr in range(16):
                instr = assemble(op, addr=addr)
                opcode, _, _, _, d_addr = decode(instr)
                assert opcode == op
                assert d_addr == addr

    def test_roundtrip_out(self):
        for rd in range(4):
            instr = assemble(OP_OUT, rd=rd)
            opcode, d_rd, _, _, _ = decode(instr)
            assert opcode == OP_OUT
            assert d_rd == rd


class TestDisassemble:
    """disassemble() 可读性测试"""

    def test_nop(self):
        assert disassemble(0x00) == "NOP"

    def test_hlt(self):
        assert disassemble(0xF0) == "HLT"

    def test_add(self):
        assert disassemble(0x37) == "ADD R1, R3"

    def test_ldi(self):
        assert disassemble(0x1B) == "LDI R2, 3"

    def test_jmp(self):
        assert disassemble(0x7A) == "JMP 0x0a"

    def test_out(self):
        assert disassemble(0x98) == "OUT R2"

    def test_undefined_opcode(self):
        result = disassemble(0xA0)
        assert "???" in result  # 未定义操作码

import pytest
from my_cpu.cpu import (
    CPU, decode, instruction_type, assemble, disassemble,
    control_unit,
    OP_NOP, OP_LDI, OP_MOV, OP_ADD, OP_SUB,
    OP_LDA, OP_STA, OP_JMP, OP_JZ, OP_OUT, OP_HLT,
    TYPE_N, TYPE_R, TYPE_I, TYPE_M,
    CTL_REG_WR, CTL_ALU_OP, CTL_MEM_WE,
    CTL_PC_LOAD, CTL_PC_INC, CTL_WB_SEL, CTL_HALT,
)


# ============================================================
#  译码器测试（从原 test_decoder.py 搬来，改 import）
# ============================================================

class TestDecode:
    def test_exhaustive_256(self):
        for instr in range(256):
            opcode, rd, rs, imm, addr = decode(instr)
            assert opcode == (instr >> 4) & 0x0F
            assert rd == (instr >> 2) & 0x03
            assert rs == instr & 0x03
            assert imm == instr & 0x03
            assert addr == instr & 0x0F

    def test_add_r1_r3(self):
        opcode, rd, rs, _, _ = decode(0x37)
        assert (opcode, rd, rs) == (OP_ADD, 1, 3)

    def test_jmp_addr_10(self):
        opcode, _, _, _, addr = decode(0x7A)
        assert (opcode, addr) == (OP_JMP, 0x0A)


class TestAssembleDecodeRoundtrip:
    def test_roundtrip_r_type(self):
        for op in [OP_MOV, OP_ADD, OP_SUB, OP_LDA, OP_STA]:
            for rd in range(4):
                for rs in range(4):
                    instr = assemble(op, rd=rd, rs=rs)
                    opcode, d_rd, d_rs, _, _ = decode(instr)
                    assert (opcode, d_rd, d_rs) == (op, rd, rs)

    def test_roundtrip_m_type(self):
        for op in [OP_JMP, OP_JZ]:
            for addr in range(16):
                instr = assemble(op, addr=addr)
                opcode, _, _, _, d_addr = decode(instr)
                assert (opcode, d_addr) == (op, addr)


# ============================================================
#  控制单元测试
# ============================================================

class TestControlUnit:
    def test_nop(self):
        ctrl = control_unit(OP_NOP, z_flag=0)
        assert ctrl[CTL_PC_INC] == 1
        assert ctrl[CTL_REG_WR] == 0
        assert ctrl[CTL_HALT] == 0

    def test_hlt(self):
        ctrl = control_unit(OP_HLT, z_flag=0)
        assert ctrl[CTL_HALT] == 1
        assert ctrl[CTL_PC_INC] == 0

    def test_add(self):
        ctrl = control_unit(OP_ADD, z_flag=0)
        assert ctrl[CTL_REG_WR] == 1
        assert ctrl[CTL_ALU_OP] == 0  # ALU_ADD
        assert ctrl[CTL_WB_SEL] == 0

    def test_jmp(self):
        ctrl = control_unit(OP_JMP, z_flag=0)
        assert ctrl[CTL_PC_LOAD] == 1
        assert ctrl[CTL_PC_INC] == 0

    def test_jz_taken(self):
        ctrl = control_unit(OP_JZ, z_flag=1)
        assert ctrl[CTL_PC_LOAD] == 1
        assert ctrl[CTL_PC_INC] == 0

    def test_jz_not_taken(self):
        ctrl = control_unit(OP_JZ, z_flag=0)
        assert ctrl[CTL_PC_LOAD] == 0
        assert ctrl[CTL_PC_INC] == 1

    def test_sta(self):
        ctrl = control_unit(OP_STA, z_flag=0)
        assert ctrl[CTL_MEM_WE] == 1
        assert ctrl[CTL_REG_WR] == 0


# ============================================================
#  CPU 集成测试（重点！）
# ============================================================

class TestCPU:
    """端到端：写程序 → 跑 → 验证寄存器/内存"""

    def _make_cpu(self, program):
        cpu = CPU(program)
        return cpu

    def _run_one(self, cpu):
        """执行一条指令（一个完整时钟周期）"""
        cpu.tick(0)
        cpu.tick(1)

    # ── NOP ──

    def test_nop_increments_pc(self):
        cpu = self._make_cpu([assemble(OP_NOP), assemble(OP_HLT)])
        self._run_one(cpu)
        assert cpu._pc_out == 1

    # ── HLT ──

    def test_hlt_stops_cpu(self):
        cpu = self._make_cpu([assemble(OP_HLT)])
        self._run_one(cpu)
        assert cpu._halted == 1
        # 再 tick 不应有变化
        pc_before = cpu._pc_out
        cpu.tick(0)
        cpu.tick(1)
        assert cpu._pc_out == pc_before

    # ── LDI ──

    def test_ldi_loads_immediate(self):
        # LDI R2, 3 → R2 = 3
        program = [assemble(OP_LDI, rd=2, imm=3), assemble(OP_HLT)]
        cpu = self._make_cpu(program)
        self._run_one(cpu)
        assert cpu._reg_outs[2] == 3

    def test_ldi_all_regs(self):
        for rd in range(4):
            for imm in range(4):
                program = [assemble(OP_LDI, rd=rd, imm=imm), assemble(OP_HLT)]
                cpu = self._make_cpu(program)
                self._run_one(cpu)
                assert cpu._reg_outs[rd] == imm

    # ── MOV ──

    def test_mov_copies_register(self):
        # LDI R0, 2; MOV R3, R0; HLT
        program = [
            assemble(OP_LDI, rd=0, imm=2),
            assemble(OP_MOV, rd=3, rs=0),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        self._run_one(cpu)  # LDI
        self._run_one(cpu)  # MOV
        assert cpu._reg_outs[3] == 2
        assert cpu._reg_outs[0] == 2  # 源不变

    # ── ADD ──

    def test_add_two_registers(self):
        # LDI R0, 1; LDI R1, 2; ADD R0, R1; HLT → R0 = 3
        program = [
            assemble(OP_LDI, rd=0, imm=1),
            assemble(OP_LDI, rd=1, imm=2),
            assemble(OP_ADD, rd=0, rs=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        for _ in range(3):
            self._run_one(cpu)
        assert cpu._reg_outs[0] == 3

    def test_add_sets_z_flag(self):
        # LDI R0, 0; LDI R1, 0; ADD R0, R1 → Z=1
        program = [
            assemble(OP_LDI, rd=0, imm=0),
            assemble(OP_LDI, rd=1, imm=0),
            assemble(OP_ADD, rd=0, rs=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        for _ in range(3):
            self._run_one(cpu)
        assert cpu._z_flag == 1
        assert cpu._reg_outs[0] == 0

    # ── SUB ──

    def test_sub_two_registers(self):
        # LDI R0, 3; LDI R1, 1; SUB R0, R1 → R0 = 2
        program = [
            assemble(OP_LDI, rd=0, imm=3),
            assemble(OP_LDI, rd=1, imm=1),
            assemble(OP_SUB, rd=0, rs=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        for _ in range(3):
            self._run_one(cpu)
        assert cpu._reg_outs[0] == 2

    def test_sub_equal_gives_zero(self):
        # LDI R0, 2; LDI R1, 2; SUB R0, R1 → R0=0, Z=1
        program = [
            assemble(OP_LDI, rd=0, imm=2),
            assemble(OP_LDI, rd=1, imm=2),
            assemble(OP_SUB, rd=0, rs=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        for _ in range(3):
            self._run_one(cpu)
        assert cpu._reg_outs[0] == 0
        assert cpu._z_flag == 1

    # ── JMP ──

    def test_jmp_skips_instructions(self):
        # addr 0: JMP 2
        # addr 1: LDI R0, 3  (应被跳过)
        # addr 2: LDI R1, 1
        # addr 3: HLT
        program = [
            assemble(OP_JMP, addr=2),
            assemble(OP_LDI, rd=0, imm=3),
            assemble(OP_LDI, rd=1, imm=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        self._run_one(cpu)  # JMP
        assert cpu._pc_out == 2
        self._run_one(cpu)  # LDI R1, 1
        assert cpu._reg_outs[1] == 1
        assert cpu._reg_outs[0] == 0  # 被跳过，未执行

    # ── JZ ──

    def test_jz_taken_when_zero(self):
        # LDI R0, 0; LDI R1, 0; ADD R0, R1 (Z=1); JZ 5; ...
        program = [
            assemble(OP_LDI, rd=0, imm=0),   # 0
            assemble(OP_LDI, rd=1, imm=0),   # 1
            assemble(OP_ADD, rd=0, rs=1),    # 2 → Z=1
            assemble(OP_JZ, addr=5),         # 3 → 跳到 5
            assemble(OP_LDI, rd=2, imm=3),   # 4 (跳过)
            assemble(OP_LDI, rd=3, imm=1),   # 5
            assemble(OP_HLT),                # 6
        ]
        cpu = self._make_cpu(program)
        for _ in range(4):
            self._run_one(cpu)
        assert cpu._pc_out == 5
        self._run_one(cpu)
        assert cpu._reg_outs[3] == 1
        assert cpu._reg_outs[2] == 0  # 被跳过

    def test_jz_not_taken_when_nonzero(self):
        # LDI R0, 1; LDI R1, 1; ADD R0, R1 (Z=0); JZ 5; LDI R2, 3; HLT
        program = [
            assemble(OP_LDI, rd=0, imm=1),   # 0
            assemble(OP_LDI, rd=1, imm=1),   # 1
            assemble(OP_ADD, rd=0, rs=1),    # 2 → R0=2, Z=0
            assemble(OP_JZ, addr=6),         # 3 → 不跳
            assemble(OP_LDI, rd=2, imm=3),   # 4 → 执行
            assemble(OP_HLT),                # 5
        ]
        cpu = self._make_cpu(program)
        for _ in range(5):
            self._run_one(cpu)
        assert cpu._reg_outs[2] == 3  # 未跳过，正常执行

    # ── STA / LDA（内存读写） ──

    def test_sta_then_lda(self):
        # LDI R0, 3; LDI R1, 2; STA R0, R1 → mem[2]=3
        # LDI R2, 0; LDA R2, R1 → R2 = mem[2] = 3
        program = [
            assemble(OP_LDI, rd=0, imm=3),   # 0: R0=3
            assemble(OP_LDI, rd=1, imm=2),   # 1: R1=2
            assemble(OP_STA, rd=0, rs=1),    # 2: mem[2]=R0=3
            assemble(OP_LDI, rd=2, imm=0),   # 3: R2=0
            assemble(OP_LDA, rd=2, rs=1),    # 4: R2=mem[2]=3
            assemble(OP_HLT),                # 5
        ]
        cpu = self._make_cpu(program)
        for _ in range(5):
            self._run_one(cpu)
        assert cpu._reg_outs[2] == 3

    # ── OUT ──

    def test_out_sets_port(self):
        # LDI R1, 3; OUT R1 → output_port = 3
        program = [
            assemble(OP_LDI, rd=1, imm=3),
            assemble(OP_OUT, rd=1),
            assemble(OP_HLT),
        ]
        cpu = self._make_cpu(program)
        self._run_one(cpu)
        self._run_one(cpu)
        assert cpu._output_port == 3

    # ── 综合：循环程序 ──

    def test_loop_sum_1_to_3(self):
        """
        计算 1+2+3 = 6 的循环程序

        伪代码：
            R0 = 0      ; sum
            R1 = 1      ; i
            R2 = 3      ; limit (用 LDI 只能到 3，刚好)
        loop:
            ADD R0, R1  ; sum += i
            LDI R3, 1   ; 常量 1
            ADD R1, R3  ; i += 1
            SUB R2, R3  ; limit -= 1
            JZ  end     ; if limit==0 goto end
            JMP loop    ; goto loop
        end:
            HLT

        期望：R0 = 6
        """
        loop_addr = 3
        end_addr = 9

        program = [
            assemble(OP_LDI, rd=0, imm=0),        # 0: R0=0 (sum)
            assemble(OP_LDI, rd=1, imm=1),        # 1: R1=1 (i)
            assemble(OP_LDI, rd=2, imm=3),        # 2: R2=3 (counter)
            # loop:
            assemble(OP_ADD, rd=0, rs=1),         # 3: sum += i
            assemble(OP_LDI, rd=3, imm=1),        # 4: R3=1
            assemble(OP_ADD, rd=1, rs=3),         # 5: i += 1
            assemble(OP_SUB, rd=2, rs=3),         # 6: counter -= 1
            assemble(OP_JZ, addr=end_addr),       # 7: if Z goto end
            assemble(OP_JMP, addr=loop_addr),     # 8: goto loop
            # end:
            assemble(OP_HLT),                     # 9
        ]
        cpu = self._make_cpu(program)
        cpu.run(max_cycles=50)

        assert cpu._halted == 1
        assert cpu._reg_outs[0] == 6, f"sum should be 6, got {cpu._reg_outs[0]}"

    # ── run() 便捷方法 ──

    def test_run_stops_at_hlt(self):
        program = [
            assemble(OP_LDI, rd=0, imm=1),
            assemble(OP_HLT),
            assemble(OP_LDI, rd=1, imm=3),  # 不应执行
        ]
        cpu = self._make_cpu(program)
        cpu.run()
        assert cpu._halted == 1
        assert cpu._reg_outs[0] == 1
        assert cpu._reg_outs[1] == 0  # HLT 后面的没跑

    def test_run_max_cycles_limit(self):
        # 死循环：JMP 0
        program = [assemble(OP_JMP, addr=0)]
        cpu = self._make_cpu(program)
        cpu.run(max_cycles=10)
        assert cpu._cycle_count == 10
        assert cpu._halted == 0  # 没 HLT，是被 max_cycles 截停的

    # ── dump_state 不崩 ──

    def test_dump_state(self):
        cpu = self._make_cpu([assemble(OP_HLT)])
        self._run_one(cpu)
        s = cpu.dump_state()
        assert "PC" in s
        assert "HLT" in s