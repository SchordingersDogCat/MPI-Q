## 
```python
# 测试基于模拟器的切割
python qcsub.py -cut -i qasms/ghz/ghz5.qasm -b Simulator -s 10240
{'00000': 0.5, '11111': 0.5}

# 测试基于模拟器运行量子线路
python qcsub.py -i qasms/ghz/ghz5.qasm -b Simulator -s 10240
{'00000': 0.5, '11111': 0.5}

# 测试基于Wukong运行量子线路
python qcsub.py -i qasms/ghz/ghz_5.qasm -b Wukong -s 10240

# 测试基于tianyan176-2运行量子线路
python qcsub.py -c qiskit -i qasms/ghz/ghz_5.qasm -b tianyan176-2 -s 10240

# 测试线路运行保真度
python qcsub.py -i  qasms/ghz/ghz_8.qasm qasms/ghz/ghz_9.qasm  -b Wukong -s 10240 -fid_test

# 测试批处理线路切割
python qcsub.py -cut  -i qasms/ghz10.qasm qasms/ghz20.qasm -b Simulator -s 10240

# 切割
python qcsub.py -cut  -i qasms/ghz20.qasm -b Simulator -s 10240

python qcsub.py -i  qasms/ghz3.qasm qasms/ghz4.qasm  -b Wukong -s 10240 -fid_test

python qcsub.py -i  qasms/ghz3.qasm qasms/ghz4.qasm qasms/ghz5.qasm qasms/ghz6.qasm qasms/ghz7.qasm qasms/ghz8.qasm qasms/ghz9.qasm  -b Wukong -s 10240 -fid_test

# 测试大规模DJ线路切割与重构，控制子线路规模为10比特
python qcsub.py -i qasms/dj/dj_balanced_500.qasm -b Simulator -cut -cut_method manual -subcirc_qubits 10 -super

# 测试在真机上的线路运行保真度
python qcsub.py -i  qasms/ghz8.qasm qasms/ghz9.qasm  -b Wukong -s 10240 -fid_test

# 测试大规模GHZ线路切割与重构
python qcsub.py -cut -cut_method manual -i qasms/ghz/ghz500.qasm -b Simulator -c qiskit -s 10240 -super

# 测试含噪声大规模量子模拟
python qcsub.py -i qasms/ghz/ghz_400.qasm -noisy_simulator 0.8 -cut -cut_method manual -subcirc_qubits 5 -super -super_nodes 64 -s 8192

# 测试大规模GHZ线路切割与重构 子线路规模不超过5
python qcsub.py -cut -cut_method manual -subcirc_qubits 5 -i qasms/ghz/ghz_2000.qasm -b Simulator -c qiskit -s 10240 -super -super_nodes 16
```