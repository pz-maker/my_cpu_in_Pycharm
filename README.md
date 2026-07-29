# my_cpu_in_Pycharm
高考后的暑假，从零开始学数字电路，用python造一个能跑的CPU，不知道AI能不能教会我~
## 🚀 My-CPU 模块完成进度

### gates.py 基础门电路 (12/12) 
- [x] nand_gate / not_gate / and_gate / or_gate / xor_gate
- [x] majority_4 / mux_2to1 / mux_4to1 / mux_8bit
- [x] _bit / split_bus_8bit / collect_bus_8bit
新增三态缓冲器，译码器
### arithmetic.py 算术单元 (3/3) 
- [x] half_adder / full_adder / ripple_carry_adder_8bit

### sequential.py 时序逻辑 (4/4) 
- [x] SRLatch (SR锁存器)
- [x] DFlipFlop (D触发器)
- [x] Register8Bit (8-bit寄存器)
- [x] ProgramCounter (程序计数器PC)

### memory.py 存储单元 (0/?) 🔜
- [ ] RAM / ROM

### cpu.py 顶层CPU (0/1) 🔜
- [ ] 指令译码 + 数据通路集成
