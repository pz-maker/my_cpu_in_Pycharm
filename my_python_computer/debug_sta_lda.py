"""
STA/LDA 数据通路追踪脚本
用法：python debug_sta_lda.py
把输出完整贴给我，我就能定位到具体哪一拍、哪个信号出了问题。
"""
from my_cpu.cpu import (
    CPU, decode, disassemble, assemble, control_unit,
    OP_LDI, OP_STA, OP_LDA, OP_HLT,
)

program = [
    assemble(OP_LDI, rd=0, imm=3),   # 0: R0=3
    assemble(OP_LDI, rd=1, imm=2),   # 1: R1=2
    assemble(OP_STA, rd=0, rs=1),    # 2: mem[2]=R0=3
    assemble(OP_LDI, rd=2, imm=0),   # 3: R2=0
    assemble(OP_LDA, rd=2, rs=1),    # 4: R2=mem[2]=3
    assemble(OP_HLT),                # 5
]

cpu = CPU(program)

for cycle in range(5):
    print(f"\n{'='*60}")
    print(f"  CYCLE {cycle}")
    print(f"{'='*60}")

    # ── clk=0 之前：打印当前状态 ──
    pc = cpu._pc_out
    instr = cpu._rom.read(pc)
    opcode, rd, rs, imm, addr_f = decode(instr)
    ctrl = control_unit(opcode, cpu._z_flag)

    print(f"  PC       = {pc}")
    print(f"  IR       = {instr:#04x}  →  {disassemble(instr)}")
    print(f"  decode   : op={opcode} rd={rd} rs={rs} imm={imm} addr={addr_f}")
    print(f"  ctrl     : wr_en={ctrl[0]} alu_op={ctrl[1]} mem_we={ctrl[2]} "
          f"pc_load={ctrl[3]} pc_inc={ctrl[4]} wb_sel={ctrl[5]} halt={ctrl[6]}")
    print(f"  reg_outs : {cpu._reg_outs}")
    print(f"  z_flag   = {cpu._z_flag}")
    print(f"  SRAM[0:4]= {[cpu._sram.read(i) for i in range(4)]}")

    # ── clk=0 ──
    cpu.tick(0)

    # ── clk=0 之后：打印 pending ──
    p = cpu._pending
    print(f"  --- after tick(0) ---")
    print(f"  pending  : rd={p['rd']} wr_en={p['reg_wr_en']} "
          f"wb_data={p['wb_data']} mem_we={p['mem_we']} "
          f"mem_addr={p['mem_addr']} mem_data={p['mem_data']}")

    # ── clk=1 ──
    cpu.tick(1)

    # ── clk=1 之后：打印结果 ──
    print(f"  --- after tick(1) ---")
    print(f"  PC       = {cpu._pc_out}")
    print(f"  reg_outs = {cpu._reg_outs}")
    print(f"  SRAM[0:4]= {[cpu._sram.read(i) for i in range(4)]}")
    print(f"  z_flag   = {cpu._z_flag}")

    # ── 直接检查每个寄存器内部 ──
    for i in range(4):
        r = cpu._reg_file._regs[i]
        print(f"  reg[{i}]._out = {r._out}   "
              f"ff_q = {[ff._q if hasattr(ff, '_q') else '?' for ff in r._ffs]}")

print(f"\n{'='*60}")
print(f"  FINAL: reg_outs = {cpu._reg_outs}")
print(f"  EXPECT: reg_outs[2] == 3")
print(f"  RESULT: {'PASS ✓' if cpu._reg_outs[2] == 3 else 'FAIL ✗'}")
print(f"{'='*60}")