"""
gates.py - 基础门电路（纯函数）
所有组合逻辑的唯一原子操作是 nand_gate，其余门均由其组合实现。
"""


def nand_gate(a: int, b: int) -> int:
    """
    与非门 (NAND) - 唯一原子门

    | a | b | out |
    |---|---|-----|
    | 0 | 0 |  1  |
    | 0 | 1 |  1  |
    | 1 | 0 |  1  |
    | 1 | 1 |  0  |
    """
    #return int(not (a and b))_v1_pass
    return 1 - (a & b)
    pass


def not_gate(a: int) -> int:
    """
    非门 (NOT)
    HW: 用 NAND 实现，将两输入端短接

    | a | out |
    |---|-----|
    | 0 |  1  |
    | 1 |  0  |
    """
    return nand_gate(a, a)
    pass


def and_gate(a: int, b: int) -> int:
    """
    与门 (AND)
    HW: NAND + NOT 组合实现

    | a | b | out |
    |---|---|-----|
    | 0 | 0 |  0  |
    | 0 | 1 |  0  |
    | 1 | 0 |  0  |
    | 1 | 1 |  1  |
    """
    return not_gate(nand_gate(a, b))
    pass


def or_gate(a: int, b: int) -> int:
    """
    或门 (OR)
    HW: 三个 NAND 组合实现 (德·摩根定律)

    | a | b | out |
    |---|---|-----|
    | 0 | 0 |  0  |
    | 0 | 1 |  1  |
    | 1 | 0 |  1  |
    | 1 | 1 |  1  |
    """
    return nand_gate(not_gate(a), not_gate(b))
    pass


def xor_gate(a: int, b: int) -> int:
    """
    异或门 (XOR)
    HW: 四个 NAND 组合实现，加法器核心元件

    | a | b | out |
    |---|---|-----|
    | 0 | 0 |  0  |
    | 0 | 1 |  1  |
    | 1 | 0 |  1  |
    | 1 | 1 |  0  |
    """
    nand_ab = nand_gate(a, b)
    left = nand_gate(a, nand_ab)
    right = nand_gate(b, nand_ab)
    return nand_gate(left, right)
    pass
def majority_4(a: int, b: int, c: int, d: int) -> int:
    """
    4输入多数表决门 (Threshold-2 Gate)
    HW: 对应"成双成对"关卡，≥2个输入为1时输出1
        用于三模冗余投票、ECC硬判决等容错场景
        实现为所有C(4,2)=6种两两AND的OR树

    | 1的个数 | out |
    |---------|-----|
    |   0     |  0  |
    |   1     |  0  |
    |   2     |  1  |
    |   3     |  1  |
    |   4     |  1  |
    """
    # HW: 6个两两AND项，覆盖所有≥2的组合
    ab = and_gate(a, b)
    ac = and_gate(a, c)
    ad = and_gate(a, d)
    bc = and_gate(b, c)
    bd = and_gate(b, d)
    cd = and_gate(c, d)

    # HW: OR树归约，3层延迟（比链式OR少1层）
    or_ab_ac = or_gate(ab, ac)
    or_ad_bc = or_gate(ad, bc)
    or_bd_cd = or_gate(bd, cd)

    or_left = or_gate(or_ab_ac, or_ad_bc)
    return or_gate(or_left, or_bd_cd)
def mux_2to1(sel: int, in0: int, in1: int) -> int:
    """
    2选1多路选择器
    HW: 数据通路基石，CPU中无处不在
        用 AND+OR 实现，避免引入新门类型
        sel=0 选 in0，sel=1 选 in1

    | sel | out |
    |-----|-----|
    |  0  | in0 |
    |  1  | in1 |
    """
    # HW: out = (¬sel ∧ in0) ∨ (sel ∧ in1)
    not_sel = not_gate(sel)
    path0 = and_gate(not_sel, in0)
    path1 = and_gate(sel, in1)
    return or_gate(path0, path1)
def _bit(val: int, n: int) -> int:
    """
    提取val的第n位（0-indexed）
    # HW: 此为仿真辅助函数，等价于硬件中从总线引出第n根导线
    # HW: 不属于被仿真的逻辑电路，仅用于信号解包
    """
    return (val >> n) & 1 #位运算符 &（末位取与）、>>（向右移一位） 直接作用于整数的二进制表示

def mux_4to1(sel: int, in0: int, in1: int, in2: int, in3: int) -> int:
    # ... docstring ...
    # HW: sel为2-bit整数，低位选组内，高位选组间，注意！！！！sel对应的物理意义是两根导线！！！！！！
    low_bit = _bit(sel, 0)   # 等价于硬件连线 sel[0]
    high_bit = _bit(sel, 1)  # 等价于硬件连线 sel[1]

    left = mux_2to1(low_bit, in0, in1)
    right = mux_2to1(low_bit, in2, in3)
    return mux_2to1(high_bit, left, right)
# ============================================================
# 总线工具：分线器 / 收线器
# ============================================================

def split_bus_8bit(data: int) -> tuple[int, int, int, int, int, int, int, int]:
    """
    8-bit 分线器 (Bus Splitter)
    HW: 把一根8-bit总线拆成8根独立的线，b0是最低位(LSB)
        相当于原理图上总线末端画的那个扇形展开符号

    | data | b7 b6 b5 b4 b3 b2 b1 b0 |
    |------|--------------------------|
    |    0 |  0  0  0  0  0  0  0  0 |
    |    5 |  0  0  0  0  0  1  0  1 |
    |  255 |  1  1  1  1  1  1  1  1 |
    |  161 |  1  0  1  0  0  0  0  1 |

    返回: (b0, b1, b2, b3, b4, b5, b6, b7)  顺序固定：低位在前
    """
    b0 = (data >> 0) & 1
    b1 = (data >> 1) & 1
    b2 = (data >> 2) & 1
    b3 = (data >> 3) & 1
    b4 = (data >> 4) & 1
    b5 = (data >> 5) & 1
    b6 = (data >> 6) & 1
    b7 = (data >> 7) & 1
    return (b0, b1, b2, b3, b4, b5, b6, b7)


def collect_bus_8bit(b0: int, b1: int, b2: int, b3: int,
                     b4: int, b5: int, b6: int, b7: int) -> int:
    """
    8-bit 收线器 (Bus Collector)
    HW: 把8根独立的线拼回一根8-bit总线，b0接最低位(LSB)
        相当于原理图上8根线汇入总线的那个扇形收束符号

    | b7 b6 b5 b4 b3 b2 b1 b0 | data |
    |--------------------------|------|
    |  0  0  0  0  0  0  0  0 |    0 |
    |  0  0  0  0  0  1  0  1 |    5 |
    |  1  1  1  1  1  1  1  1 |  255 |
    |  1  0  1  0  0  0  0  1 |  161 |

    输入顺序: b0(LSB) ~ b7(MSB)，与 split_bus_8bit 返回顺序一致
    """
    return (b0 << 0) | (b1 << 1) | (b2 << 2) | (b3 << 3) | (b4 << 4) | (b5 << 5) | (b6 << 6) | (b7 << 7)

def mux_8bit(sel: int, in0: int, in1: int) -> int:
    """
    8-bit 宽 2选1多路选择器（逐位调用 mux_2to1）

    | sel | out   |
    |-----|-------|
    |  0  | in0   |
    |  1  | in1   |

    参数： 
        sel : 0 或 1
        in0 : 0~255（sel=0 时选中）
        in1 : 0~255（sel=1 时选中）
    返回：
        int, 0~255
    """
    bits_0 = split_bus_8bit(in0)
    bits_1 = split_bus_8bit(in1)
    # HW: 逐位独立选择，各位之间无耦合（§7.5 bit-slice 原则）
    out_bits = tuple(mux_2to1(sel, b0, b1) for b0, b1 in zip(bits_0, bits_1))
    return collect_bus_8bit(*out_bits)

def decoder_2to4(a0:int, a1:int) -> tuple[int, int, int, int]:
    '''译码器，第一个纯手搓元件,丑陋无比，但忠实硬件原理'''
    zero_addr = a0
    zero_addr_bar = not_gate(zero_addr)
    one_addr = a1
    one_addr_bar = not_gate(one_addr)
    sel0 = and_gate(zero_addr_bar, one_addr_bar)
    sel1 = and_gate(zero_addr_bar, one_addr)
    sel2 = and_gate(zero_addr, one_addr_bar)
    sel3 = and_gate(zero_addr, one_addr)
    return sel0, sel1, sel2, sel3

# 这不是一个"门电路"，而是对三态缓冲器的行为级建模
def tristate_buf(q: int, re: int) -> int:
    """
    三态缓冲器

    | re | out |
    |----|-----|
    |  0 |  -1 |  ← 高阻态，与总线断开
    |  1 |  q  |  ← 直通
    """
    # HW: 真实硬件是传输门(PMOS+NMOS)，
    # 仿真中用 -1 约定表示 Z 态，仅在总线模块使用
    return q if re == 1 else -1