OPENQASM 2.0;
include "qelib1.inc";  // 包含标准量子门库

qreg q[4];
creg c[4];

h q[2];
cx q[2], q[3];
ry(pi/4) q[1];
rz(pi/2) q[3];
cx q[1], q[2];