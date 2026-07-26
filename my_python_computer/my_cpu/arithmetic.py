from my_cpu.gates import xor_gate, and_gate

from my_cpu.gates import xor_gate, and_gate, or_gate


def half_adder(a: int, b: int) -> tuple[int, int]:
    """
    半加器 (Half Adder)
    HW: 加法器最小单元，不含进位输入
        sum 用 XOR（不同为1），cout 用 AND（全1才进位）
        全加器 = 两个半加器 + 一个 OR 门

    | a | b | sum | cout |
    |---|---|-----|------|
    | 0 | 0 |  0  |  0   |
    | 0 | 1 |  1  |  0   |
    | 1 | 0 |  1  |  0   |
    | 1 | 1 |  0  |  1   |
    """
    sum_ = xor_gate(a, b)
    cout = and_gate(a, b)
    return (sum_, cout)


def full_adder(a: int, b: int, cin: int) -> tuple[int, int]:
    """
    全加器 (Full Adder)
    HW: 两个半加器级联 + OR门合并进位
        第一级: a + b → sum1, cout1
        第二级: sum1 + cin → sum2, cout2
        最终进位: cout1 OR cout2（任一级产生进位即输出1）

    | a | b | cin | sum | cout |
    |---|---|-----|-----|------|
    | 0 | 0 |  0  |  0  |  0   |
    | 0 | 0 |  1  |  1  |  0   |
    | 0 | 1 |  0  |  1  |  0   |
    | 0 | 1 |  1  |  0  |  1   |
    | 1 | 0 |  0  |  1  |  0   |
    | 1 | 0 |  1  |  0  |  1   |
    | 1 | 1 |  0  |  0  |  1   |
    | 1 | 1 |  1  |  1  |  1   |
    """
    # HW: 第一级半加器处理 a+b
    sum1, cout1 = half_adder(a, b)
    # HW: 第二级半加器把低位进位 cin 加进来
    sum2, cout2 = half_adder(sum1, cin)
    # HW: 两级进位取 OR —— 任意一级产生进位，最终就进位
    cout = or_gate(cout1, cout2)
    return (sum2, cout)
from my_cpu.gates import split_bus_8bit, collect_bus_8bit


def ripple_carry_adder_8bit(a: int, b: int, cin: int = 0) -> tuple[int, int]:
    """
    8-bit 行波进位加法器（Ripple Carry Adder）

    将 a、b 两个 8-bit 整数逐位相加，进位从 LSB 向 MSB 逐级传递。

    真值表（简化，以 4-bit 示意原理）：

    | a    | b    | cin | sum  | cout |
    |------|------|-----|------|------|
    | 0x00 | 0x00 |  0  | 0x00 |  0   |
    | 0xFF | 0x01 |  0  | 0x00 |  1   |
    | 0xFF | 0xFF |  0  | 0xFE |  1   |
    | 0xFF | 0xFF |  1  | 0xFF |  1   |
    | 0x80 | 0x80 |  0  | 0x00 |  1   |

    参数:
        a:   8-bit 被加数 (0~255)
        b:   8-bit 加数   (0~255)
        cin: 进位输入     (0 或 1)

    返回:
        (sum, cout)
        sum:  8-bit 结果 (0~255，溢出截断)
        cout: 进位输出   (0 或 1)
    """
    # HW: 先用分线器把总线拆成8根独立导线，模拟物理上每根线连一个FA
    a_bits = split_bus_8bit(a)  # (a0, a1, ..., a7) 低位在前
    b_bits = split_bus_8bit(b)  # (b0, b1, ..., b7)

    # HW: 行波进位——每个FA的cout直接喂给下一个FA的cin，
    #     模拟进位信号从bit0一路"波纹"传播到bit7
    carry = cin#函数内操作，不要影响外部电路
    sum_bits = []
    for i in range(8):
        s, carry = full_adder(a_bits[i], b_bits[i], carry)
        sum_bits.append(s)

    # HW: 收线器把8根结果线拼回总线整数
    result = collect_bus_8bit(*sum_bits)#*有解包功能 ❌ 不加 *：把整个列表当作第一个参数传进去

    return (result, carry)
