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
    """

    def __init__(self):
        # 4行 × 4列 = 16 个独立锁存器
        self._cells = [[ReadAndWriteLatch() for _ in range(4)] for _ in range(4)]

    def tick(self, clk: int, addr: int, d_in: int, we: int, re: int) -> int:
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

