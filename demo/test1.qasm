// 6比特量子电路
OPENQASM 2.0;
include "qelib1.inc";

// 声明6个量子比特和6个经典比特
qreg q[6];
creg c[6];

// 量子门操作 - 创建一个更复杂的电路
h q[0];          // 对第一个量子比特应用Hadamard门
cx q[0], q[1];   // CNOT门，创建纠缠
h q[2];          // 对第三个量子比特应用Hadamard门
cx q[2], q[3];   // CNOT门，创建纠缠
h q[4];          // 对第五个量子比特应用Hadamard门
cx q[4], q[5];   // CNOT门，创建纠缠

// 进一步的操作，连接不同的量子比特组
cx q[1], q[2];   // 连接第一组和第二组
cx q[3], q[4];   // 连接第二组和第三组

measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];

    
