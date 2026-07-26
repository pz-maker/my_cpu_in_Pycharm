"""
tests/test_gates.py - 基础门电路穷举测试
"""
import pytest
from my_cpu.arithmetic import ripple_carry_adder_8bit
class TestRippleCarryAdder8Bit:
    """穷举 + 边界用例"""

    def test_exhaustive_cin0(self):
        """穷举 cin=0 的全部 256×256 = 65536 种组合"""
        for a in range(256):
            for b in range(256):
                s, cout = ripple_carry_adder_8bit(a, b, 0)
                expected = a + b
                assert s == expected & 0xFF, f"a={a}, b={b}, cin=0"
                assert cout == (expected >> 8) & 1

    def test_exhaustive_cin1(self):
        """穷举 cin=1 的全部 65536 种组合"""
        for a in range(256):
            for b in range(256):
                s, cout = ripple_carry_adder_8bit(a, b, 1)
                expected = a + b + 1
                assert s == expected & 0xFF, f"a={a}, b={b}, cin=1"
                assert cout == (expected >> 8) & 1

    def test_zero_plus_zero(self):
        assert ripple_carry_adder_8bit(0, 0, 0) == (0, 0)

    def test_max_plus_one(self):
        """0xFF + 0x01 = 0x100 → sum=0x00, cout=1"""
        assert ripple_carry_adder_8bit(0xFF, 0x01, 0) == (0x00, 1)

    def test_max_plus_max(self):
        """0xFF + 0xFF = 0x1FE → sum=0xFE, cout=1"""
        assert ripple_carry_adder_8bit(0xFF, 0xFF, 0) == (0xFE, 1)

    def test_max_plus_max_cin1(self):
        """0xFF + 0xFF + 1 = 0x1FF → sum=0xFF, cout=1"""
        assert ripple_carry_adder_8bit(0xFF, 0xFF, 1) == (0xFF, 1)

    def test_overflow_boundary(self):
        """0x80 + 0x80 = 0x100 → sum=0x00, cout=1"""
        assert ripple_carry_adder_8bit(0x80, 0x80, 0) == (0x00, 1)

    def test_no_overflow_boundary(self):
        """0x7F + 0x01 = 0x80 → sum=0x80, cout=0"""
        assert ripple_carry_adder_8bit(0x7F, 0x01, 0) == (0x80, 0)

