import pytest

from my_cpu.sequential import SRLatch, GatedDLatch, DFlipFlop


def test_sr_latch():
    """
    SR Latch 穷举测试 + 状态保持验证
    HW: SR Latch 是异步电平敏感元件，没有时钟概念，
        所以直接用 update() 传入不同的 s_bar/r_bar 组合即可。
    """
    latch = SRLatch()

    # 1. 初始状态：NAND实现的SR Latch上电默认输出 (1, 1)
    #    （因为两个NAND门输入初始为0时输出为1）
    #however 我们预设初始稳态为01或10，避免上电亚稳态导致仿真不确定
    q, q_bar = latch.update(1, 1)
    assert (q, q_bar) in [(0, 1), (1, 0)], f"初始状态接受任意合法稳态，实际({q},{q_bar})"

    # 2. Set: s_bar=0 → Q=1, Q_bar=0
    q, q_bar = latch.update(0, 1)
    assert q == 1 and q_bar == 0, f"Set失败: ({q},{q_bar})"

    # 3. 保持: 回到(1,1)后应维持上一次的状态
    q, q_bar = latch.update(1, 1)
    assert q == 1 and q_bar == 0, f"Set后保持失败: ({q},{q_bar})"

    # 4. Reset: r_bar=0 → Q=0, Q_bar=1
    q, q_bar = latch.update(1, 0)
    assert q == 0 and q_bar == 1, f"Reset失败: ({q},{q_bar})"

    # 5. 保持: 再次验证复位后的保持
    q, q_bar = latch.update(1, 1)
    assert q == 0 and q_bar == 1, f"Reset后保持失败: ({q},{q_bar})"

    # 6. 非法状态: s_bar=0, r_bar=0 → 双1（NAND特性）
    q, q_bar = latch.update(0, 0)
    assert q == 1 and q_bar == 1, f"非法状态应为(1,1)，实际({q},{q_bar})"

    print("✅ SRLatch 全部测试通过")


def test_gated_d_latch():
    """
    门控D锁存器测试
    HW: 重点验证 en=0 时的"锁存隔离"能力——
        无论 d 怎么跳变，Q 都必须纹丝不动。
    """
    latch = GatedDLatch()

    # 1. en=0 时，初始输出应为0（SRLatch经转换后的稳态）
    q = latch.update(en=0, d=0)
    assert q == 0, f"en=0初始应为0，实际{q}"

    # 2. en=1 透传: d=1 → Q=1
    q = latch.update(en=1, d=1)
    assert q == 1, f"en=1,d=1 透传失败: {q}"

    # 3. en=1 透传: d=0 → Q=0
    q = latch.update(en=1, d=0)
    assert q == 0, f"en=1,d=0 透传失败: {q}"

    # 4. 🔑 核心测试: en=0 锁存
    #    先让 en=1,d=1 把内部充到1，然后关使能
    latch.update(en=1, d=1)
    q = latch.update(en=0, d=1)
    assert q == 1, f"en=0应保持1，实际{q}"

    # 5. 🔑 核心测试: en=0 期间 d 翻转，Q 不变
    q = latch.update(en=0, d=0)  # d从1变0
    assert q == 1, f"en=0时d变化不应影响Q! 期望1，实际{q}"
    q = latch.update(en=0, d=1)  # d再从0变1
    assert q == 1, f"en=0时d变化不应影响Q! 期望1，实际{q}"

    print("✅ GatedDLatch 全部测试通过")


def test_d_flip_flop():
    """
    D触发器完整时序测试
    HW: 这是最重要的测试！我们用一个精确设计的时钟+数据序列，
        一次性覆盖：上升沿采样、高电平保持、下降沿保持、低电平透明(Master)。

        时序图示意（每个 tick 对应一行）：
        clk: 0 → 1 → 1 → 0 → 0 → 1 → 1 → 0
        d:   1 → 1 → 0 → 0 → 1 → 0 → 1 → 1
        Q:   0 → 1 → 1 → 1 → 1 → 0 → 0 → 0
             ↑     ↑           ↑
          初始  上升沿采1   上升沿采0
               (d变0无效)  (d变1无效)
    """
    ff = DFlipFlop()

    # 定义测试向量: (clk, d, expected_q, 说明)
    # HW: 用列表而非字典，保证执行顺序严格可控
    test_vectors = [
        # --- 第一阶段：验证初始状态与首次上升沿 ---
        (0, 1, 0, "clk=0: Master透明吸d=1, Slave锁存→Q=0"),
        (1, 1, 1, "↑上升沿: Master锁1, Slave透明→Q=1"),
        (1, 0, 1, "clk=1保持: d变0但Master已关门→Q仍=1"),

        # --- 第二阶段：验证下降沿保持与低电平Master透明 ---
        (0, 0, 1, "↓下降沿: Slave锁存→Q保持1; Master开始吸d=0"),
        (0, 1, 1, "clk=0: Master改吸d=1, Slave仍锁→Q=1"),

        # --- 第三阶段：验证第二次上升沿采样新值 ---
        (1, 1, 1, "↑上升沿: Master锁1→Slave传出→Q=1"),
        (1, 0, 1, "clk=1保持: d变0无效→Q=1"),

        # --- 第四阶段：准备下一次采样0 ---
        (0, 0, 1, "↓下降沿: Q保持1; Master吸d=0"),
        (1, 0, 0, "↑上升沿: Master锁0→Slave传出→Q=0 ✅"),
        (1, 1, 0, "clk=1保持: d变1无效→Q=0 ✅"),
    ]

    for i, (clk, d, expected_q, desc) in enumerate(test_vectors):
        actual_q = ff.tick(clk=clk, d=d)
        assert actual_q == expected_q, (
            f"Step {i} 失败!\n"
            f"  描述: {desc}\n"
            f"  输入: clk={clk}, d={d}\n"
            f"  期望Q={expected_q}, 实际Q={actual_q}"
        )

    print("✅ DFlipFlop 全部时序测试通过")


# HW: Python 测试文件的入口守卫
#     直接运行此文件时执行测试；被 pytest 等框架导入时不自动执行
if __name__ == "__main__":
    test_sr_latch()
    test_gated_d_latch()
    test_d_flip_flop()
    print("\n🎉 sequential.py 所有测试全部通过！")



from my_cpu.sequential import ProgramCounter


def _full_cycle(pc, rst, load, inc, data_in):
    """辅助：执行一个完整时钟周期（两拍），返回 tick(1) 的结果"""
    pc.tick(clk=0, rst=rst, load=load, inc=inc, data_in=data_in)
    return pc.tick(clk=1, rst=rst, load=load, inc=inc, data_in=data_in)


def test_rst_overrides_all():
    """rst=1 时，无论 load/inc 如何，输出 0x00"""
    pc = ProgramCounter()
    assert _full_cycle(pc, rst=1, load=1, inc=1, data_in=0xAB) == 0x00


def test_load_jump():
    """load=1, inc=1 同时有效 → load 赢"""
    pc = ProgramCounter()
    assert _full_cycle(pc, rst=0, load=1, inc=1, data_in=0x3C) == 0x3C


def test_inc_sequence():
    """连续自增：0 → 1 → 2 → 3"""
    pc = ProgramCounter()
    _full_cycle(pc, rst=1, load=0, inc=0, data_in=0)   # 复位到 0
    for expected in (1, 2, 3):
        assert _full_cycle(pc, rst=0, load=0, inc=1, data_in=0) == expected


def test_hold():
    """所有控制为 0 → 值不变"""
    pc = ProgramCounter()
    _full_cycle(pc, rst=0, load=1, inc=0, data_in=0x55)  # 先加载 0x55
    assert _full_cycle(pc, rst=0, load=0, inc=0, data_in=0) == 0x55


def test_overflow_wrap():
    """0xFF + 1 = 0x00（8-bit 自然回绕）"""
    pc = ProgramCounter()
    _full_cycle(pc, rst=0, load=1, inc=0, data_in=0xFF)
    assert _full_cycle(pc, rst=0, load=0, inc=1, data_in=0) == 0x00


def test_data_in_truncation():
    """data_in=0x1FF → 截断为 0xFF"""
    pc = ProgramCounter()
    assert _full_cycle(pc, rst=0, load=1, inc=0, data_in=0x1FF) == 0xFF


def test_two_cycle_load_then_inc():
    """加载 → 自增，验证跨周期状态传递"""
    pc = ProgramCounter()
    _full_cycle(pc, rst=0, load=1, inc=0, data_in=0x10)  # PC ← 0x10
    assert _full_cycle(pc, rst=0, load=0, inc=1, data_in=0) == 0x11  # PC ← 0x11
