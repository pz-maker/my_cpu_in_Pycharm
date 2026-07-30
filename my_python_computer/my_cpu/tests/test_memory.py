import pytest
from my_cpu.memory import SRAM16x8, MemoryArray4x4


class TestMemoryArray4x4Read:
    """验证新增的异步 read 方法"""

    def test_read_after_write(self):
        """写入后异步读回"""
        mem = MemoryArray4x4()
        # 写 addr=5, d_in=1（两拍）
        mem.tick(clk=0, addr=5, d_in=1, we=1, re=0)
        mem.tick(clk=1, addr=5, d_in=1, we=1, re=0)
        # 异步读
        assert mem.read(5) == 1
        assert mem.read(0) == 0  # 未写入地址仍为 0

    def test_read_does_not_modify(self):
        """读操作不改变存储内容"""
        mem = MemoryArray4x4()
        mem.tick(clk=0, addr=3, d_in=1, we=1, re=0)
        mem.tick(clk=1, addr=3, d_in=1, we=1, re=0)
        # 连续读多次，值不变
        assert mem.read(3) == 1
        assert mem.read(3) == 1
        assert mem.read(3) == 1


class TestSRAM16x8:
    """8-bit × 16 字 SRAM 完整测试"""

    def test_write_then_read_all_addresses(self):
        """写入 16 个地址，逐一读回验证"""
        sram = SRAM16x8()
        test_data = [i * 17 % 256 for i in range(16)]

        for addr in range(16):
            sram.tick(clk=0, cs=1, we=1, addr=addr, data_in=test_data[addr])
            sram.tick(clk=1, cs=1, we=1, addr=addr, data_in=test_data[addr])

        for addr in range(16):
            result = sram.tick(clk=0, cs=1, we=0, addr=addr, data_in=0)
            assert result == test_data[addr], f"addr={addr}: 期望 {test_data[addr]}, 得到 {result}"

    def test_cs_inactive_returns_high_z(self):
        """片选无效时返回高阻态"""
        sram = SRAM16x8()
        assert sram.tick(clk=0, cs=0, we=0, addr=0, data_in=0xFF) == -1
        assert sram.tick(clk=1, cs=0, we=1, addr=0, data_in=0xFF) == -1

    def test_write_does_not_affect_other_addresses(self):
        """写 addr=5 不影响 addr=3"""
        sram = SRAM16x8()
        sram.tick(clk=0, cs=1, we=1, addr=3, data_in=0xAB)
        sram.tick(clk=1, cs=1, we=1, addr=3, data_in=0xAB)
        sram.tick(clk=0, cs=1, we=1, addr=5, data_in=0xCD)
        sram.tick(clk=1, cs=1, we=1, addr=5, data_in=0xCD)
        assert sram.tick(clk=0, cs=1, we=0, addr=3, data_in=0) == 0xAB

    def test_overwrite(self):
        """同一地址覆盖写入"""
        sram = SRAM16x8()
        sram.tick(clk=0, cs=1, we=1, addr=7, data_in=0x11)
        sram.tick(clk=1, cs=1, we=1, addr=7, data_in=0x11)
        sram.tick(clk=0, cs=1, we=1, addr=7, data_in=0x22)
        sram.tick(clk=1, cs=1, we=1, addr=7, data_in=0x22)
        assert sram.tick(clk=0, cs=1, we=0, addr=7, data_in=0) == 0x22

    def test_bit_independence(self):
        """验证 8 个位切片互不干扰"""
        sram = SRAM16x8()
        # 只写 bit0
        sram.tick(clk=0, cs=1, we=1, addr=0, data_in=0b00000001)
        sram.tick(clk=1, cs=1, we=1, addr=0, data_in=0b00000001)
        assert sram.tick(clk=0, cs=1, we=0, addr=0, data_in=0) == 0b00000001

        # 只写 bit7
        sram.tick(clk=0, cs=1, we=1, addr=1, data_in=0b10000000)
        sram.tick(clk=1, cs=1, we=1, addr=1, data_in=0b10000000)
        assert sram.tick(clk=0, cs=1, we=0, addr=1, data_in=0) == 0b10000000

    def test_full_byte_pattern(self):
        """写入 0xA5 (10100101) 验证各位正确"""
        sram = SRAM16x8()
        sram.tick(clk=0, cs=1, we=1, addr=9, data_in=0xA5)
        sram.tick(clk=1, cs=1, we=1, addr=9, data_in=0xA5)
        result = sram.tick(clk=0, cs=1, we=0, addr=9, data_in=0)
        assert result == 0xA5
        # 逐位验证
        from my_cpu.gates import split_bus_8bit
        bits = split_bus_8bit(result)
        assert bits == (1, 0, 1, 0, 0, 1, 0, 1)  # b0~b7

from my_cpu.memory import ROM16x8


class TestROM16x8:
    """ROM16x8 完整测试"""

    # ── 基本读取 ──

    def test_read_all_addresses(self):
        """16 个地址逐一读出，与烧录内容一致"""
        program = [0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87,
                   0x98, 0xA9, 0xBA, 0xCB, 0xDC, 0xED, 0xFE, 0x0F]
        rom = ROM16x8(program)
        for addr in range(16):
            assert rom.read(addr) == program[addr], f"addr={addr}"

    def test_read_returns_int(self):
        """返回值是 int，不是 bool / None"""
        rom = ROM16x8([0xFF])
        result = rom.read(0)
        assert isinstance(result, int)
        assert result == 255

    # ── 不足 16 字自动补零 ──

    def test_short_program_padded_with_zero(self):
        """程序不足 16 字，剩余地址读出 0x00"""
        rom = ROM16x8([0xAA, 0xBB])
        assert rom.read(0) == 0xAA
        assert rom.read(1) == 0xBB
        for addr in range(2, 16):
            assert rom.read(addr) == 0x00, f"addr={addr} 应为 0x00"

    def test_empty_program_all_zero(self):
        """空程序 → 全部读出 0"""
        rom = ROM16x8([])
        for addr in range(16):
            assert rom.read(addr) == 0x00

    # ── 超出 16 字截断 ──

    def test_long_program_truncated(self):
        """超过 16 字的部分被丢弃"""
        program = list(range(32))  # 0~31，共 32 字
        rom = ROM16x8(program)
        assert rom.read(0) == 0
        assert rom.read(15) == 15
        # addr=16 不存在，但 4-bit 地址自动回绕到 0
        assert rom.read(16) == rom.read(0)

    # ── 地址截断（4-bit 回绕） ──

    def test_addr_wraps_at_4_bits(self):
        """addr > 15 时只取低 4 位（硬件只有 4 根地址线）"""
        rom = ROM16x8([0x42])
        assert rom.read(0) == 0x42
        assert rom.read(16) == 0x42   # 16 & 0x0F == 0
        assert rom.read(17) == 0x00   # 17 & 0x0F == 1，未写入 → 0
        assert rom.read(255) == 0x00  # 255 & 0x0F == 15 → 0

    # ── 只读不可变 ──

    def test_data_is_immutable(self):
        """构造后无法修改内容（tuple 保证）"""
        rom = ROM16x8([0xFF])
        with pytest.raises(TypeError):
            rom._data[0] = 0x00  # type: ignore

    # ── 纯组合逻辑：无状态、无副作用 ──

    def test_repeated_read_same_result(self):
        """连续读同一地址，结果永远一致（无状态）"""
        rom = ROM16x8([0xDE, 0xAD])
        for _ in range(100):
            assert rom.read(0) == 0xDE
            assert rom.read(1) == 0xAD

    def test_read_order_irrelevant(self):
        """读取顺序不影响结果（组合逻辑无记忆）"""
        program = [i * 11 % 256 for i in range(16)]
        rom = ROM16x8(program)
        # 倒序读
        for addr in range(15, -1, -1):
            assert rom.read(addr) == program[addr]
        # 跳读
        assert rom.read(7) == program[7]
        assert rom.read(3) == program[3]
        assert rom.read(7) == program[7]

    # ── 边界值 ──

    def test_all_ff(self):
        """全 0xFF 程序"""
        rom = ROM16x8([0xFF] * 16)
        for addr in range(16):
            assert rom.read(addr) == 255

    def test_all_zero(self):
        """全 0x00 程序"""
        rom = ROM16x8([0x00] * 16)
        for addr in range(16):
            assert rom.read(addr) == 0

    def test_single_instruction(self):
        """只有一条指令的极简程序"""
        rom = ROM16x8([0b11110000])  # 假设 HLT = 0xF0
        assert rom.read(0) == 0xF0
        assert rom.read(1) == 0x00  # 后续全是 NOP/空白