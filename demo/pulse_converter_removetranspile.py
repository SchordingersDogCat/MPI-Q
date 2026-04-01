import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit import pulse
from qiskit import transpile  # 保留导入但不再使用
from qiskit.compiler  import schedule
from qiskit.providers  import Backend
from qiskit import assemble
from qiskit import qasm2
from qiskit.pulse  import Schedule, Play, Waveform
from qiskit_aer import Aer
from qiskit_aer import AerSimulator
import time
import argparse
import sys
import os
import psutil
import gc

# def get_memory_usage():
#     """获取当前进程的内存使用情况（MB）"""
#     process = psutil.Process(os.getpid())
#     return process.memory_info().rss / 1024 / 1024  # 转换为MB

# def print_memory_usage(label, start_mem=None):
#     """打印内存使用情况，可选计算增量"""
#     current_mem = get_memory_usage()
#     if start_mem is not None:
#         delta = current_mem - start_mem
#         print(f"[内存监控] {label}: {current_mem:.2f} MB (增量: {delta:+.2f} MB)")
#     else:
#         print(f"[内存监控] {label}: {current_mem:.2f} MB")
#     return current_mem

# # ========== 内存监控装饰器 ==========
# def monitor_memory(func):
#     """内存监控装饰器"""
#     def wrapper(*args, **kwargs):
#         start_mem = get_memory_usage()
#         start_time = time.time()
        
#         print(f"\n[内存监控] 开始执行: {func.__name__}")
#         result = func(*args, **kwargs)
        
#         end_time = time.time()
#         end_mem = get_memory_usage()
        
#         print(f"[内存监控] {func.__name__} 完成:")
#         print(f"          耗时: {end_time-start_time:.2f}秒")
#         print(f"          内存变化: {end_mem-start_mem:+.2f} MB")
        
#         return result
#     return wrapper

import qiskit
print(qiskit.__version__) # 查看版本
import qiskit.providers.fake_provider as fp
print([attr for attr in dir(fp) if 'Fake' in attr]) # 查看所有可用的 Fake 后端

# 导入matplotlib用于绘图
import matplotlib.pyplot as plt

from qiskit.providers.fake_provider import Fake27QPulseV1

# ========== 新增：获取连接量子比特的函数 ==========
def get_connected_qubits(backend, num_qubits_needed):
    """
    获取后端中相互连接的量子比特
    
    参数:
        backend: 量子后端
        num_qubits_needed (int): 需要的量子比特数量
    
    返回:
        dict: 量子比特映射字典 {逻辑索引: 物理索引}
    """
    coupling_map = backend.configuration().coupling_map
    print(f"Backend coupling map: {coupling_map}")
    
    # 寻找包含足够数量量子比特的连接组
    visited = set()
    
    for start_qubit in range(backend.configuration().num_qubits):
        if start_qubit in visited:
            continue
            
        # 使用BFS寻找连接组件
        connected_component = []
        queue = [start_qubit]
        
        while queue and len(connected_component) < num_qubits_needed:
            current = queue.pop(0)
            if current not in connected_component:
                connected_component.append(current)
                visited.add(current)
                
                # 添加相邻量子比特
                for connection in coupling_map:
                    if connection[0] == current and connection[1] not in connected_component:
                        queue.append(connection[1])
                    elif connection[1] == current and connection[0] not in connected_component:
                        queue.append(connection[0])
        
        # 如果找到足够大的连接组件
        if len(connected_component) >= num_qubits_needed:
            mapping = {i: connected_component[i] for i in range(num_qubits_needed)}
            print(f"Found connected qubits: {mapping}")
            return mapping
    
    # 如果找不到完全连接的，返回前num_qubits_needed个
    default_mapping = {i: i for i in range(min(num_qubits_needed, backend.configuration().num_qubits))}
    print(f"Using default mapping: {default_mapping}")
    return default_mapping

# ========== 创建统一的脉冲生成类 ==========
class QasmToPulseConverter:
    """
    QASM到脉冲转换器类
    提供用户接口，将QASM量子线路转换为脉冲波形
    """
    
    def __init__(self, backend=None, qubit_mapping=None, auto_connect=True, include_measurement_pulses=False):
        """
        初始化转换器
        
        参数:
            backend: 量子后端，如果为None则使用默认后端
            qubit_mapping: 量子比特映射字典，例如 {0: 36, 1: 51, 2: 50}
        """
        
        # # ========== 新增：记录初始内存 ==========
        # self.initial_memory = get_memory_usage()
        # print(f"[内存监控] 转换器初始化前: {self.initial_memory:.2f} MB")

        self.backend = backend if backend else Fake27QPulseV1()
        print(f"Using backend: {self.backend.name}")
        print(f"Backend supports OpenPulse: {self.backend.configuration().open_pulse}")
        
        # ========== 修改点1：添加测量脉冲选项 ==========
        self.include_measurement_pulses = include_measurement_pulses
        print(f"Include measurement pulses: {self.include_measurement_pulses}")
        
        # 初始化时还不知道需要多少量子比特，所以先不设置映射
        self.qubit_mapping = qubit_mapping
        self.auto_connect = auto_connect
        
        if qubit_mapping is not None:
            print(f"Using user-provided qubit mapping: {self.qubit_mapping}")
        else:
            print("Qubit mapping will be determined based on QASM circuit")

        # # ========== 新增：记录初始化后内存 ==========
        # mem_after_init = print_memory_usage("转换器初始化后", self.initial_memory)

    def _determine_qubit_mapping(self, num_qubits_needed):
        """
        根据需要的量子比特数量确定映射
        
        参数:
            num_qubits_needed: 需要的量子比特数量
        """
        if self.qubit_mapping is not None:
            # 检查用户提供的映射是否足够
            if len(self.qubit_mapping) >= num_qubits_needed:
                print(f"Using user-provided qubit mapping: {self.qubit_mapping}")
                # 如果用户提供的映射比需要的多，只取需要的部分
                if len(self.qubit_mapping) > num_qubits_needed:
                    self.qubit_mapping = {i: self.qubit_mapping[i] for i in range(num_qubits_needed)}
                    print(f"Trimmed user mapping to: {self.qubit_mapping}")
                return
            else:
                print(f"Warning: User mapping has {len(self.qubit_mapping)} qubits but need {num_qubits_needed}")
        
        # 自动确定映射
        if self.auto_connect:
            self.qubit_mapping = get_connected_qubits(self.backend, num_qubits_needed)
            print(f"Using auto-connected qubit mapping: {self.qubit_mapping}")
        else:
            # 使用默认映射
            self.qubit_mapping = {i: i for i in range(num_qubits_needed)}
            print(f"Using default qubit mapping: {self.qubit_mapping}")
    

    # ========== 修改点2：添加测量脉冲生成方法 ==========
    def _generate_measurement_pulses(self, circuit_duration, num_qubits):
        """
        生成测量脉冲
        
        参数:
            circuit_duration: 量子门操作的总时长
            num_qubits: 量子比特数量
            
        返回:
            dict: 测量脉冲字典 {量子位索引: 测量脉冲数组}
        """
        measurement_pulses = {}
        
        # 获取后端配置
        config = self.backend.configuration()
        defaults = self.backend.defaults()
        
        # 获取采样时间
        dt = config.dt
        
        # 测量脉冲参数
        measure_duration = getattr(config, 'measure_duration', 1000)  # 默认1微秒
        measure_amplitude = 0.3  # 测量脉冲幅度
        
        print(f"Generating measurement pulses with duration {measure_duration} dt")
        
        for qubit_idx in range(num_qubits):
            # 获取物理量子比特索引
            physical_qubit = self.qubit_mapping.get(qubit_idx, qubit_idx)
        
            # 获取测量频率（如果可用）
            try:
                measure_freq = defaults.measure_freq_est[physical_qubit]
            except (AttributeError, IndexError):
                # 如果无法获取测量频率，使用量子比特频率
                try:
                    measure_freq = defaults.qubit_freq_est[physical_qubit]
                except (AttributeError, IndexError):
                    measure_freq = 6.0e9  # 默认6 GHz
        
        # 创建测量脉冲（在量子门操作之后）
        measure_start = circuit_duration
        measure_end = measure_start + measure_duration
        
        # 创建测量脉冲包络 - 使用更平滑的形状
        t_measure = np.arange(measure_duration) * dt
        
        # 使用高斯包络而不是矩形包络
        sigma = measure_duration / 6  # 高斯包络的标准差
        gaussian_envelope = measure_amplitude * np.exp(-0.5 * ((t_measure - measure_duration/2) / sigma)**2)
        
        # 调制到测量频率
        carrier = np.exp(2j * np.pi * measure_freq * t_measure)
        measure_pulse = gaussian_envelope * carrier
        
        # 创建完整的脉冲数组（包含前面的零填充）
        full_measure_pulse = np.zeros(measure_end, dtype=complex)
        full_measure_pulse[measure_start:measure_end] = measure_pulse
        
        measurement_pulses[qubit_idx] = full_measure_pulse
        
        print(f"  Qubit {qubit_idx} (physical {physical_qubit}): measurement pulse at {measure_start}-{measure_end} dt, "
              f"frequency {measure_freq/1e9:.2f} GHz, duration {measure_duration*dt*1e9:.2f} ns")
    
        return measurement_pulses
    

    def qasm_to_pulse_waveforms(self, qasm_str: str) -> dict:
        """
        将 QASM 量子线路转换为波形脉冲数组
        
        参数:
            qasm_str (str): OpenQASM 2.0 格式的量子线路字符串
        
        返回:
            dict: 键为量子位索引，值为该量子位通道的波形脉冲数组（复数数组）
        """
        
        # # ========== 新增：记录解析前内存 ==========
        # mem_before_parse = print_memory_usage("QASM解析前")

        # 解析 QASM 字符串为 QuantumCircuit 对象
        qc = QuantumCircuit.from_qasm_str(qasm_str) 
        print("Original circuit:")
        print(qc)

        # 获取电路中的量子比特数量
        num_qubits_in_circuit = qc.num_qubits
        print(f"Circuit uses {num_qubits_in_circuit} qubits")
        
        # ========== 修改：动态确定量子比特映射 ==========
        self._determine_qubit_mapping(num_qubits_in_circuit)

        # # ========== 新增：记录解析后内存 ==========
        # mem_after_parse = print_memory_usage("QASM解析后", mem_before_parse)

        # ========== 修改：移除transpile，直接使用映射 ==========
        print("\nUsing direct qubit mapping (no transpilation)")
        print(f"Logical to physical mapping: {self.qubit_mapping}")
        
        # 创建新的量子电路，应用映射
        # 计算需要的物理量子比特数量
        max_physical_qubit = max(self.qubit_mapping.values()) if self.qubit_mapping else 0
        num_physical_qubits = max_physical_qubit + 1

        # ========== 修改：创建包含经典寄存器的映射电路 ==========
        # 获取原始电路的经典比特数量
        num_clbits = qc.num_clbits
        mapped_qc = QuantumCircuit(num_physical_qubits, num_clbits)
        print(f"Mapped circuit has {len(mapped_qc.qubits)} physical qubits and {num_clbits} classical bits")

        # ========== 修改：改进指令处理逻辑，处理测量操作 ==========
        # 复制原电路的所有操作，应用量子比特映射
        for instruction in qc:
            # 获取操作名称用于调试
            op_name = instruction.operation.name
            
            # 处理测量操作
            if op_name == 'measure':
                # 测量操作需要同时处理量子比特和经典比特
                if len(instruction.qubits) != 1 or len(instruction.clbits) != 1:
                    print(f"Warning: Unexpected measure operation format: {instruction}")
                    continue
                
                qubit = instruction.qubits[0]
                clbit = instruction.clbits[0]
                
                # 获取逻辑量子比特索引
                logical_index = qc.qubits.index(qubit)
                # 映射到物理量子比特
                if logical_index in self.qubit_mapping:
                    physical_index = self.qubit_mapping[logical_index]
                    mapped_qubit = mapped_qc.qubits[physical_index]
                else:
                    # 如果没有映射，使用原索引
                    mapped_qubit = mapped_qc.qubits[logical_index]
                
                # 经典比特保持不变
                mapped_clbit = mapped_qc.clbits[qc.clbits.index(clbit)]
                
                # 添加映射后的测量指令
                mapped_qc.measure(mapped_qubit, mapped_clbit)
                
            else:
                # 非测量操作：只处理量子比特
                mapped_qubits = []
                for qubit in instruction.qubits:
                    # 获取逻辑量子比特索引
                    logical_index = qc.qubits.index(qubit)
                    # 映射到物理量子比特
                    if logical_index in self.qubit_mapping:
                        physical_index = self.qubit_mapping[logical_index]
                        mapped_qubits.append(mapped_qc.qubits[physical_index])
                    else:
                        # 如果没有映射，使用原索引
                        mapped_qubits.append(mapped_qc.qubits[logical_index])
                
                # 添加映射后的指令
                mapped_qc.append(instruction.operation, mapped_qubits)
        
        print("Mapped circuit:")
        print(mapped_qc)

        # ========== 修改点4：根据是否包含测量脉冲决定是否移除测量操作 ==========
        if not self.include_measurement_pulses:
            # 创建不包含测量的电路用于脉冲生成
            pulse_qc = mapped_qc.copy()
            
            # 移除所有测量操作，因为脉冲调度不需要测量
            pulse_qc.remove_final_measurements()
            
            print("Circuit for pulse generation (measurements removed):")
            print(pulse_qc)
        else:
            # 保留测量操作用于调度
            pulse_qc = mapped_qc
            print("Circuit for pulse generation (including measurements):")
            print(pulse_qc)

        # 应用transpile，优化级别为0，禁用路由
        print("\nApplying transpile with optimization_level=0 and no routing")
        try:
            transpiled_qc = transpile(
                pulse_qc,  # 使用不包含测量的电路
                self.backend, 
                optimization_level=0,
                routing_method='none',  # 禁用路由
                layout_method='trivial'  # 使用原始布局
            )
        except Exception as e:
            print(f"Routing failed, using basic transpile: {e}")
            transpiled_qc = transpile(pulse_qc, self.backend, optimization_level=0)
        
        print("Transpiled circuit:")
        print(transpiled_qc)
        print(f"Transpiled circuit uses {len(transpiled_qc.qubits)} qubits")

        #  # ========== 新增：记录映射后内存 ==========
        # mem_after_mapping = print_memory_usage("比特映射完成", mem_after_parse)

        # 将量子电路调度为脉冲 Schedule
        sched = schedule(transpiled_qc, self.backend)

        # # ========== 新增：记录调度后内存 ==========
        # mem_after_schedule = print_memory_usage("脉冲调度后", mem_after_mapping)
        
        # 分析调度中的指令
        print("\n=== Schedule Analysis ===")
        qubit_usage = set()
        
        for time, inst in sched.instructions:
            if isinstance(inst, Play):
                channel = inst.channel
                if hasattr(channel, 'index'):
                    qubit = channel.index
                    qubit_usage.add(qubit)
        
        print(f"Qubits used in schedule: {sorted(qubit_usage)}")
        print(f"Our mapped qubits: {list(self.qubit_mapping.values())}")

        # 提取波形脉冲数组
        pulse_arrays = {}
        # 重构指令处理逻辑
        qubit_channels = {}
        
        # 首先收集所有量子位相关的通道
        for time, inst in sched.instructions:
            if isinstance(inst, Play):
                channel = inst.channel
                # 根据通道类型确定量子位
                if hasattr(channel, 'index'):
                    qubit = channel.index
                    if qubit not in qubit_channels:
                        qubit_channels[qubit] = []
                    qubit_channels[qubit].append((time, inst))
        
        # 为每个量子位创建时间序列
        for qubit, instructions in qubit_channels.items():
            # 按时间排序
            instructions.sort(key=lambda x: x[0])
            
            # 计算总长度
            total_duration = 0
            for time, inst in instructions:
                pulse_obj = inst.pulse
                if isinstance(pulse_obj, Waveform):
                    duration = len(pulse_obj.samples)
                elif hasattr(pulse_obj, 'duration'):
                    duration = pulse_obj.duration
                else:
                    duration = 0
                
                # 更新总时长
                end_time = time + duration
                if end_time > total_duration:
                    total_duration = end_time
            
            # 创建全零数组
            pulse_array = np.zeros(total_duration, dtype=complex)
            
            # 填充脉冲数据
            for time, inst in instructions:
                pulse_obj = inst.pulse
                
                # 处理不同类型的脉冲对象
                if isinstance(pulse_obj, Waveform):
                    # 对于 Waveform 对象，直接获取样本
                    pulse_data = pulse_obj.samples
                    duration = len(pulse_data)
                elif hasattr(pulse_obj, 'get_waveform'):
                    # 对于 ScalableSymbolicPulse 和其他参数化脉冲，先转换为 Waveform
                    try:
                        waveform = pulse_obj.get_waveform()
                        pulse_data = waveform.samples
                        duration = len(pulse_data)
                    except Exception as e:
                        print(f"Error converting parametric pulse to waveform: {e}")
                        continue
                else:
                    # 其他未知类型的脉冲
                    print(f"Unsupported pulse type: {type(pulse_obj)}")
                    continue
                
                # 将脉冲数据插入到正确的时间位置
                start_idx = time
                end_idx = time + duration
                if end_idx <= total_duration:
                    pulse_array[start_idx:end_idx] = pulse_data
            
            pulse_arrays[qubit] = pulse_array
        #  # ========== 新增：记录波形提取后内存 ==========
        # mem_after_extract = print_memory_usage("波形提取完成", mem_after_schedule)
        # print(f"[内存监控] 生成的脉冲数组数量: {len(pulse_arrays)}")
        # for qubit, array in pulse_arrays.items():
        #     print(f"[内存监控]   量子位 {qubit}: {len(array)} 个样本, 占用 {array.nbytes/1024/1024:.2f} MB")
        
        print(f"\nGenerated pulse arrays for {len(pulse_arrays)} qubits: {list(pulse_arrays.keys())}")
    
        # 过滤，只保留映射中的量子比特
        filtered_pulse_arrays = {}
        for qubit in self.qubit_mapping.values():
            if qubit in pulse_arrays:
                filtered_pulse_arrays[qubit] = pulse_arrays[qubit]
            else:
                # 创建空数组表示该量子比特没有脉冲
                filtered_pulse_arrays[qubit] = np.array([], dtype=complex)
        
        print(f"Filtered to {len(filtered_pulse_arrays)} mapped qubits: {list(filtered_pulse_arrays.keys())}")
        
        # ========== 修改点5：如果需要，生成测量脉冲 ==========
        if self.include_measurement_pulses:
            print("\n=== Generating Measurement Pulses ===")
            
            # 计算量子门操作的总时长
            gate_duration = 0
            for qubit, pulse_array in filtered_pulse_arrays.items():
                if len(pulse_array) > gate_duration:
                    gate_duration = len(pulse_array)
            
            print(f"Gate operation duration: {gate_duration} samples")
            
            # 生成测量脉冲
            measurement_pulses = self._generate_measurement_pulses(gate_duration, len(self.qubit_mapping))
            
            # 合并门脉冲和测量脉冲
            combined_pulses = {}
            for qubit in self.qubit_mapping.values():
                gate_pulse = filtered_pulse_arrays.get(qubit, np.array([], dtype=complex))
                measure_pulse = measurement_pulses.get(qubit, np.array([], dtype=complex))
                
                # 修复脉冲合并逻辑
                if len(measure_pulse) > 0:
                    # 计算总长度
                    total_length = max(len(gate_pulse), len(measure_pulse))
                    
                    # 创建新的复数数组，分别合并实部和虚部
                    combined_pulse = np.zeros(total_length, dtype=complex)
                    
                    # 添加门脉冲
                    if len(gate_pulse) > 0:
                        combined_pulse[:len(gate_pulse)] += gate_pulse
                    
                    # 添加测量脉冲（使用复数加法而不是最大值）
                    if len(measure_pulse) > 0:
                        # 确保measure_pulse长度与combined_pulse一致
                        if len(measure_pulse) < total_length:
                            temp_measure = np.zeros(total_length, dtype=complex)
                            temp_measure[:len(measure_pulse)] = measure_pulse
                            measure_pulse = temp_measure
                        combined_pulse += measure_pulse
                    
                    combined_pulses[qubit] = combined_pulse
                else:
                    combined_pulses[qubit] = gate_pulse
            
            print(f"Generated {len(measurement_pulses)} measurement pulses")
            return {
                'gate_pulses': filtered_pulse_arrays,
                'measurement_pulses': measurement_pulses,
                'combined_pulses': combined_pulses
            }
        else:
            return {
                'gate_pulses': filtered_pulse_arrays,
                'measurement_pulses': {},
                'combined_pulses': filtered_pulse_arrays
            }
        

    def envelope_to_real_waveforms(self, pulse_arrays):
        """
        将包络信号转换为真实的载波调制波形
        
        参数:
            pulse_arrays (dict): 基带包络信号
        
        返回:
            dict: 包含真实波形的字典
        """
        real_waveforms = {}
        
        # 获取后端的配置信息
        config = self.backend.configuration()
        defaults = self.backend.defaults()
        
        # 获取采样时间
        dt = config.dt  # 采样间隔时间

        # # ========== 新增：记录转换前内存 ==========
        # mem_before_convert = print_memory_usage("开始包络转换前")
        
        # 为每个量子位生成真实波形
        for qubit, envelope in pulse_arrays.items():
            # 获取量子位的驱动频率
            try:
                # 尝试从后端获取量子位频率
                qubit_freq = defaults.qubit_freq_est[qubit]
            except (AttributeError, IndexError):
                # 如果无法获取，使用默认频率 (例如 5 GHz)
                qubit_freq = 5.0e9  # 5 GHz
            
            # 创建时间轴
            t = np.arange(len(envelope)) * dt
            
            # 生成载波信号
            carrier = np.exp(2j * np.pi * qubit_freq * t)
            
            # 将包络调制到载波上，生成真实波形
            real_waveform = envelope * carrier
            
            real_waveforms[qubit] = real_waveform

            # ========== 新增：记录每个量子位的波形大小 ==========
            print(f"[内存监控]   量子位 {qubit} 真实波形: {len(real_waveform)} 样本, 占用 {real_waveform.nbytes/1024/1024:.2f} MB")
        
        # # ========== 新增：记录转换后内存 ==========
        # mem_after_convert = print_memory_usage("包络转换完成", mem_before_convert)
        
        return real_waveforms

    def plot_real_waveforms(self, real_waveforms, title_suffix=""):
        """
        绘制真实波形
        
        参数:
            real_waveforms (dict): 真实波形字典
            title_suffix (str): 标题后缀
        """
        if not real_waveforms:
            print("No real waveform data to plot.")
            return
        
        # 获取采样时间
        dt = self.backend.configuration().dt
        
        # 创建子图
        num_qubits = len(real_waveforms)
        fig, axes = plt.subplots(num_qubits, 1, figsize=(12, 4*num_qubits))
        
        # 如果只有一个量子位，确保axes是数组
        if num_qubits == 1:
            axes = [axes]
        
        for i, (qubit, waveform) in enumerate(real_waveforms.items()):
            # 创建时间轴 (纳秒)
            t_ns = np.arange(len(waveform)) * dt * 1e9
            
            # 修复：对数据进行降采样以避免过于密集
            if len(waveform) > 10000:  # 如果数据点太多，进行降采样
                step = len(waveform) // 5000  # 目标约5000个点
                if step < 1:
                    step = 1
                indices = np.arange(0, len(waveform), step)
                t_ns_plot = t_ns[indices]
                waveform_plot = np.real(waveform)[indices]
            else:
                t_ns_plot = t_ns
                waveform_plot = np.real(waveform)

            # 绘制真实波形 (取实部作为实际发送的信号)
            axes[i].plot(t_ns, np.real(waveform), 'b-', linewidth=1.5, label='Real Waveform')
            axes[i].set_title(f'Qubit {qubit} - Real Waveform (Modulated){title_suffix}')
            axes[i].set_xlabel('Time (ns)')
            axes[i].set_ylabel('Amplitude')
            axes[i].grid(True, alpha=0.3)
            axes[i].legend()
            
            # 添加频率信息
            try:
                defaults = self.backend.defaults()
                qubit_freq = defaults.qubit_freq_est[qubit]
                axes[i].text(0.02, 0.95, f'Frequency: {qubit_freq/1e9:.2f} GHz', 
                            transform=axes[i].transAxes, fontsize=10,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            except:
                pass
    
        plt.tight_layout()
        plt.show()

    def plot_comparison(self, pulse_arrays, real_waveforms):
        """
        同时显示包络和真实波形以进行比较
        
        参数:
            pulse_arrays (dict): 包络信号
            real_waveforms (dict): 真实波形
        """
        if not pulse_arrays or not real_waveforms:
            print("No data to plot.")
            return
        
        # 获取采样时间
        dt = self.backend.configuration().dt
        
        # 创建子图
        num_qubits = len(pulse_arrays)
        fig, axes = plt.subplots(num_qubits, 2, figsize=(15, 4*num_qubits))
        
        # 如果只有一个量子位，确保axes是二维数组
        if num_qubits == 1:
            axes = axes.reshape(1, -1)
        
        for i, qubit in enumerate(pulse_arrays.keys()):
            envelope = pulse_arrays[qubit]
            real_waveform = real_waveforms[qubit]
            
            # 创建时间轴 (纳秒)
            t_ns = np.arange(len(envelope)) * dt * 1e9
            
            # 修复：对数据进行降采样
            def downsample_data(t, data, max_points=5000):
                if len(data) > max_points:
                    step = len(data) // max_points
                    if step < 1:
                        step = 1
                    indices = np.arange(0, len(data), step)
                    return t[indices], data[indices]
                return t, data
            
            
            # 绘制包络 (第一列)
            t_env, env_i = downsample_data(t_ns, np.real(envelope))
            t_env, env_q = downsample_data(t_ns, np.imag(envelope))

            axes[i, 0].plot(t_ns, np.real(envelope), 'g-', linewidth=2, label='Envelope (I)')
            axes[i, 0].plot(t_ns, np.imag(envelope), 'r-', linewidth=2, label='Envelope (Q)')
            axes[i, 0].set_title(f'Qubit {qubit} - Baseband Envelope')
            axes[i, 0].set_xlabel('Time (ns)')
            axes[i, 0].set_ylabel('Amplitude')
            axes[i, 0].grid(True)
            axes[i, 0].legend()
            
            # 绘制真实波形 (第二列)
            t_real, real_data = downsample_data(t_ns, np.real(real_waveform))
            axes[i, 1].plot(t_real, real_data, 'b-', linewidth=1.0, label='Real Waveform')

            axes[i, 1].set_title(f'Qubit {qubit} - Modulated Waveform')
            axes[i, 1].set_xlabel('Time (ns)')
            axes[i, 1].set_ylabel('Amplitude')
            axes[i, 1].grid(True)
            axes[i, 1].legend()
            
            # 添加频率信息
            try:
                defaults = self.backend.defaults()
                qubit_freq = defaults.qubit_freq_est[qubit]
                axes[i, 1].text(0.02, 0.95, f'Frequency: {qubit_freq/1e9:.2f} GHz', 
                               transform=axes[i, 1].transAxes, fontsize=10,
                               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            except:
                pass
        
        plt.tight_layout()
        plt.show()

    def plot_measurement_pulses_only(self, measurement_pulses):
        """
        专门绘制测量脉冲
        
        参数:
            measurement_pulses (dict): 测量脉冲字典
        """
        if not measurement_pulses:
            print("No measurement pulse data to plot.")
            return
        
        # 获取采样时间
        dt = self.backend.configuration().dt
        
        # 创建子图
        num_qubits = len(measurement_pulses)
        fig, axes = plt.subplots(num_qubits, 1, figsize=(12, 4*num_qubits))
        
        # 如果只有一个量子位，确保axes是数组
        if num_qubits == 1:
            axes = [axes]
        
        for i, (qubit, pulse) in enumerate(measurement_pulses.items()):
            # 找到非零部分的起始和结束
            nonzero_indices = np.where(np.abs(pulse) > 1e-10)[0]
            if len(nonzero_indices) == 0:
                print(f"No measurement pulse found for qubit {qubit}")
                continue
                
            start_idx = nonzero_indices[0]
            end_idx = nonzero_indices[-1] + 1
            
            # 提取非零部分
            measurement_section = pulse[start_idx:end_idx]
            t_ns = np.arange(len(measurement_section)) * dt * 1e9
            
            # 绘制测量脉冲
            axes[i].plot(t_ns, np.real(measurement_section), 'r-', linewidth=1.5, label='Measurement Pulse')
            
            axes[i].set_title(f'Qubit {qubit} - Measurement Pulse')
            axes[i].set_xlabel('Time (ns)')
            axes[i].set_ylabel('Amplitude')
            axes[i].grid(True, alpha=0.3)
            axes[i].legend()
            
            # 添加脉冲信息
            pulse_duration = len(measurement_section) * dt * 1e9
            max_amplitude = np.max(np.abs(measurement_section))
            axes[i].text(0.02, 0.95, f'Duration: {pulse_duration:.2f} ns\nMax Amp: {max_amplitude:.3f}', 
                        transform=axes[i].transAxes, fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        plt.tight_layout()
        plt.show()

    def analyze_real_waveforms(self, real_waveforms):
        """分析真实波形数据"""
        print("\n=== Real Waveform Analysis ===")
        dt = self.backend.configuration().dt
        
        for qubit, waveform in real_waveforms.items():
            # 获取量子位频率
            try:
                defaults = self.backend.defaults()
                qubit_freq = defaults.qubit_freq_est[qubit]
            except:
                qubit_freq = 5.0e9  # 默认5 GHz
            
            print(f"Qubit {qubit}:")
            print(f"  Total duration: {len(waveform)} samples ({len(waveform)*dt*1e9:.2f} ns)")
            print(f"  Carrier frequency: {qubit_freq/1e9:.2f} GHz")
            print(f"  Max amplitude: {np.max(np.abs(waveform)):.4f}")
            print(f"  RMS amplitude: {np.sqrt(np.mean(np.abs(waveform)**2)):.4f}")
            
            # 计算带宽相关信息
            if len(waveform) > 1:
                # 简单的带宽估计
                spectrum = np.fft.fft(np.real(waveform))
                freqs = np.fft.fftfreq(len(waveform), dt)
                positive_freqs = freqs[:len(freqs)//2]
                positive_spectrum = np.abs(spectrum[:len(spectrum)//2])
                
                # 找到主频率
                main_freq_idx = np.argmax(positive_spectrum)
                main_freq = positive_freqs[main_freq_idx]
                print(f"  Main frequency in waveform: {main_freq/1e9:.2f} GHz")

    # ========== 主要处理函数即用户接口 ==========
    def process_qasm(self, qasm_source, source_type="string"):
        """
        处理QASM量子线路并生成脉冲波形
        
        参数:
            qasm_source (str): QASM字符串或文件路径
            source_type (str): "string"表示QASM字符串，"file"表示文件路径
        
        返回:
            dict: 包含处理结果的字典
        """

        # # ========== 新增：记录处理前总内存 ==========
        # total_start_memory = get_memory_usage()
        total_start_time = time.time()
        
        # print(f"[内存监控] 开始处理QASM，当前内存: {total_start_memory:.2f} MB")
        
        # 处理QASM输入
        if source_type == "file":
            if not os.path.exists(qasm_source):
                print(f"Error: QASM file '{qasm_source}' not found.")
                return {"error": "File not found"}
            
            with open(qasm_source, 'r') as f:
                qasm_str = f.read()
            print(f"Loaded QASM from file: {qasm_source}")
        else:
            qasm_str = qasm_source
            print("Using provided QASM string")
        
        print("\nQASM String:")
        print(qasm_str)
        
        # 转换为脉冲包络
        print("\nConverting QASM to pulse waveforms...")
        pulse_results = self.qasm_to_pulse_waveforms(qasm_str)
        
        if not pulse_results:
            print("Error: No pulse data generated")
            return {"error": "No pulse data generated"}
        
        print("Baseband envelope summary:")
        gate_pulses = pulse_results.get('gate_pulses', {})
        measurement_pulses = pulse_results.get('measurement_pulses', {})
        combined_pulses = pulse_results.get('combined_pulses', {})
        
        for qubit, data in gate_pulses.items():
            print(f"Qubit {qubit} gate pulse: length = {len(data)}")
        
        for qubit, data in measurement_pulses.items():
            print(f"Qubit {qubit} measurement pulse: length = {len(data)}")


        # 将包络转换为真实波形
        print("\nConverting envelope to real waveforms...")
        real_gate_waveforms = self.envelope_to_real_waveforms(gate_pulses)
        real_measurement_waveforms = self.envelope_to_real_waveforms(measurement_pulses)
        real_combined_waveforms = self.envelope_to_real_waveforms(combined_pulses)
        
        print("Real waveforms summary:")
        for qubit, data in real_gate_waveforms.items():
            print(f"Qubit {qubit}: length = {len(data)}")
            print(f"  First 3000 samples: {np.real(data[:3000])}")
        
        for qubit, data in real_measurement_waveforms.items():
            print(f"Qubit {qubit} measurement waveform: length = {len(data)}")

        # 总体时间统计
        total_end_time = time.time()
        total_execution_time = total_end_time - total_start_time

        # # ========== 新增：记录处理后总内存 ==========
        # total_end_memory = get_memory_usage()
        # total_memory_increase = total_end_memory - total_start_memory
        
        print(f"\n=== Total Execution Time Summary ===")
        print(f"Total execution time: {total_execution_time:.2f} seconds")
        
        # 绘制比较图和真实波形
        print("\nGenerating plots...")
        if self.include_measurement_pulses:
            # 分别绘制门脉冲、测量脉冲和合并脉冲
            self.plot_comparison(gate_pulses, real_gate_waveforms)
            self.plot_measurement_pulses_only(measurement_pulses)  # 新增：专门绘制测量脉冲
            self.plot_real_waveforms(real_combined_waveforms, " - Combined (Gates + Measurement)")
        else:
            self.plot_comparison(gate_pulses, real_gate_waveforms)
            self.plot_real_waveforms(real_gate_waveforms)
        
        # 分析真实波形
        self.analyze_real_waveforms(real_combined_waveforms)                            
        
        # 返回处理结果
        return {
            "gate_pulses": gate_pulses,
            "measurement_pulses": measurement_pulses,
            "combined_pulses": combined_pulses,
            "real_gate_waveforms": real_gate_waveforms,
            "real_measurement_waveforms": real_measurement_waveforms,
            "real_combined_waveforms": real_combined_waveforms,
            "execution_time": total_execution_time,
            "num_qubits": len(gate_pulses),
            "qubit_mapping": self.qubit_mapping,
            "include_measurement": self.include_measurement_pulses
        }


def monitor_script_execution():
    # """
    # 监控整个脚本执行过程的内存使用
    # """
    # script_start_mem = get_memory_usage()
    # print(f"[内存监控] 脚本开始执行，当前内存: {script_start_mem:.2f} MB")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 从字符串生成脉冲
        qasm_str = """
        OPENQASM 2.0;
        include "qelib1.inc";

        qreg q[5];
        creg c[5];

        h q[0];
        cx q[0], q[1];
        cx q[1], q[2];  
        cx q[2], q[3];  
        cx q[3], q[4];  
       
        """
        
        print("=== 测试1: 从字符串生成脉冲 ===")
        result1 = generate_pulses_from_qasm(qasm_str, include_measurement_pulses=True)
        print(f"测试1完成，处理了 {result1.get('num_qubits', 0)} 个量子位")
        
        # # ========== 新增：测试间内存清理 ==========
        # print("\n[内存监控] 执行测试间回收...")
        # gc.collect()
        # mem_after_gc = print_memory_usage("测试间回收后")
        
        print("\n=== 测试2: 从文件生成脉冲 ===")
        # 从文件生成脉冲
        result2 = generate_pulses_from_qasm("ghz3.qasm", is_file=True, include_measurement_pulses=True)
        print(f"测试2完成，处理了 {result2.get('num_qubits', 0)} 个量子位")
        
        # 返回所有结果
        return {
            "result1": result1,
            "result2": result2,
            # "start_memory": script_start_mem,
            "start_time": start_time
        }
        
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        return {"error": str(e)}

# ========== 命令行接口 ==========
def main():
    """
    主函数 - 提供命令行接口
    """

    # # ========== 新增：记录程序开始内存 ==========
    # program_start_memory = get_memory_usage()

    parser = argparse.ArgumentParser(description="Convert QASM quantum circuits to pulse waveforms")
    parser.add_argument("qasm_input", nargs="?", help="QASM string or file path")
    parser.add_argument("-f", "--file", action="store_true", 
                       help="Treat input as file path (default is string)")
    parser.add_argument("-e", "--example", action="store_true", 
                       help="Run with example QASM circuit")
    # ========== 修改：添加量子比特映射参数 ==========
    parser.add_argument("-m", "--mapping", type=str, 
                       help="Qubit mapping as string, e.g., '0:36,1:51,2:50'")
    parser.add_argument("-a", "--auto-connect", action="store_true", default=True,
                       help="Automatically find connected qubits (default: True)")
    # ========== 修改点7：添加测量脉冲命令行参数 ==========
    parser.add_argument("--include-measurement", action="store_true", default=False,
                       help="Include measurement pulses in output (default: False)")
    
    args = parser.parse_args()
    
    # ========== 修改：解析量子比特映射 ==========
    qubit_mapping = None
    if args.mapping:
        try:
            qubit_mapping = {}
            pairs = args.mapping.split(',')
            for pair in pairs:
                logical, physical = pair.split(':')
                qubit_mapping[int(logical)] = int(physical)
            print(f"Using custom qubit mapping: {qubit_mapping}")
        except Exception as e:
            print(f"Error parsing qubit mapping: {e}")
            return 1
    
         # ========== 修改：创建转换器，使用智能映射 ==========
    converter = QasmToPulseConverter(
        qubit_mapping=qubit_mapping, 
        auto_connect=args.auto_connect,
        include_measurement_pulses=args.include_measurement  # 添加测量脉冲选项
    )
    
    # 处理输入
    if args.example:
        # 使用示例QASM
        example_qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[2];

        h q[0];
        cx q[0], q[1];
        measure q -> c;
        """
        print("Running with example QASM circuit...")
        result = converter.process_qasm(example_qasm, source_type="string")
    
    elif args.qasm_input:
        # 使用用户提供的输入
        source_type = "file" if args.file else "string"
        result = converter.process_qasm(args.qasm_input, source_type=source_type)
    
    else:
        # 没有提供输入，显示帮助
        parser.print_help()
        print("\nNo input provided. Running with example QASM circuit...")
        example_qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        creg c[3];

        h q[0];
        h q[1];
        x q[2];
        measure q -> c;
        """
        result = converter.process_qasm(example_qasm, source_type="string")
        return
    
    # 检查结果
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    
    # # ========== 新增：程序结束内存统计 ==========
    # program_end_memory = get_memory_usage()
    # program_total_increase = program_end_memory - program_start_memory
    
    # print(f"\n=== 程序总内存统计 ===")
    # print(f"程序启动内存: {program_start_memory:.2f} MB")
    # print(f"程序结束内存: {program_end_memory:.2f} MB")
    # print(f"程序总内存增加: {program_total_increase:.2f} MB")
    
    print(f"\nProcessing completed successfully!")
    print(f"Processed {result['num_qubits']} qubits in {result['execution_time']:.2f} seconds")
    print(f"Qubit mapping used: {result.get('qubit_mapping', 'N/A')}")
    print(f"Included measurement pulses: {result.get('include_measurement', False)}")
    
    return 0

# ========== 直接调用函数 ==========
def generate_pulses_from_qasm(qasm_input, is_file=False, qubit_mapping=None, auto_connect=True, include_measurement_pulses=False):
    """
    直接从QASM生成脉冲的简便函数
    
    参数:
        qasm_input (str): QASM字符串或文件路径
        is_file (bool): 如果为True，则将qasm_input视为文件路径
        qubit_mapping (dict): 量子比特映射字典
        auto_connect (bool): 是否自动选择连接的量子比特
    
    返回:
        dict: 处理结果
    """
    
    converter = QasmToPulseConverter(
        qubit_mapping=qubit_mapping, 
        auto_connect=auto_connect,
        include_measurement_pulses=include_measurement_pulses  # 添加测量脉冲选项
    )
    source_type = "file" if is_file else "string"
    wave_dict = (converter.process_qasm(qasm_input, source_type=source_type))["real_combined_waveforms"]
    for key,value in wave_dict.items():
        wave_dict[key] = value.tolist()
    return wave_dict

# ========== 新增：如果直接运行则启动内存监控 ==========
# ========== 修改：主执行块 ==========
if __name__ == "__main__":
    # # 记录脚本开始时的内存
    # script_start_mem = get_memory_usage()
    # print(f"[内存监控] 脚本启动内存: {script_start_mem:.2f} MB")
    
    # 执行监控的脚本
    final_result = monitor_script_execution()
    
    # # 记录脚本结束时的内存
    # script_end_mem = get_memory_usage()
    script_total_time = time.time() - final_result.get("start_time", time.time())
    
    # print(f"\n=== 脚本执行总结 ===")
    # print(f"总执行时间: {script_total_time:.2f} 秒")
    # print(f"脚本启动内存: {script_start_mem:.2f} MB")
    # print(f"脚本结束内存: {script_end_mem:.2f} MB")
    # print(f"脚本总内存变化: {script_end_mem - script_start_mem:+.2f} MB")
    
    # 检查文件编码的代码（注释状态）
    # with open("ghz.qasm", 'rb') as f:
    #     raw_content = f.read()
    #     print("Raw content:", raw_content)
    #     print("Decoded:", raw_content.decode('utf-8'))
    
    # # ========== 新增：最终内存清理 ==========
    # print("\n[内存监控] 执行最终回收...")
    # gc.collect()
    # final_mem = print_memory_usage("最终回收后", script_end_mem)
    
    print(f"\n脚本执行完成!")
# else:
#     # ========== 新增：当脚本被导入时的处理 ==========
#     print(f"[内存监控] 脚本被导入为模块，当前内存: {get_memory_usage():.2f} MB")

