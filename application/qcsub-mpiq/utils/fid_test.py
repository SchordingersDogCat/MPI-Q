from qiskit.quantum_info.analysis import hellinger_fidelity
import os,ast

# 自定义排序键函数
def sort_key(item):
    # 提取 name 字段中的数字部分
    number = int(''.join(filter(str.isdigit, os.path.basename(item))))
    return number

def txt_to_dict(file_path):
    """
    将特定格式的txt文件转换为字典
    
    参数：
    file_path (str): 文本文件路径
    
    返回：
    dict: 解析后的字典，格式为 {字符串键: 整型值}
    """
    result = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                # 预处理行内容
                cleaned_line = line.strip()
                
                # 跳过空行
                if not cleaned_line:
                    continue
                
                # 分割键值对
                if ':' not in cleaned_line:
                    print(f"[第{line_number}行] 格式错误：缺少冒号分隔符 -> '{cleaned_line}'")
                    continue
                
                # 分割键值（最多分割一次）
                key, _, value = cleaned_line.partition(':')
                
                # 验证键有效性
                if not key:
                    print(f"[第{line_number}行] 无效键：空键 -> '{cleaned_line}'")
                    continue
                
                # 转换数值
                try:
                    numeric_value = int(value)
                except ValueError:
                    print(f"[第{line_number}行] 值转换失败：'{value}' 无法转为整数")
                    continue
                
                # 存储结果（处理重复键）
                if key in result:
                    print(f"[第{line_number}行] 警告：重复键 '{key}'，将覆盖前值")
                result[key] = numeric_value
                
    except FileNotFoundError:
        print(f"错误：文件不存在 {file_path}")
        return {}
    except Exception as e:
        print(f"读取文件时发生意外错误：{str(e)}")
        return {}
    
    return result

def dictTxt_to_dict(file_path):
    """
    将特定格式的txt文件转换为字典
    
    参数：
    file_path (str): 文本文件路径
    
    返回：
    dict: 解析后的字典，格式为 {字符串键: 整型值}
    """
    result = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
            result = ast.literal_eval(result)
 
    except FileNotFoundError:
        print(f"错误：文件不存在 {file_path}")
        return {}
    except Exception as e:
        print(f"读取文件时发生意外错误：{str(e)}")
        return {}
    
    return result

def get_res(root_dir):
    # 当操作系统的任务调度结束即返回结果时使用该后处理函数，使用场景为
    # 1.操作系统任务调度 QCSUB -i test.qasm
    # 遍历root_dir目录及其子目录
    # root_dir = f"../{root_dir}"
    result_dict = []
    file_path_list = os.listdir(f"{root_dir}")
    file_path_list = sorted(file_path_list, key=sort_key)
    print("file_paths:",file_path_list)
    for l1_entry in file_path_list:
        l1_path = os.path.join(root_dir, l1_entry)
        if os.path.isdir(l1_path):
            for l2_entry in os.listdir(l1_path):
                l2_path = os.path.join(root_dir, l1_entry, l2_entry)
                if os.path.isdir(l2_path):
                    for l3_entry in os.listdir(l2_path):
                        if l3_entry.endswith(".txt"):
                            full_path = os.path.join(root_dir, l1_entry, l2_entry, l3_entry)
                            print(full_path)
                            content = dictTxt_to_dict(full_path)
                            result_dict.append(content) 
    return result_dict

def get_simulator_res(sub_circuit_res_path, shots):
    from qiskit import Aer,execute,QuantumCircuit
    res_list = []
    for cir_path in sub_circuit_res_path:    
        with open(f"{cir_path}", 'r') as f:
            cir = f.read()
        backend = Aer.get_backend('qasm_simulator')
        qc = QuantumCircuit.from_qasm_str(cir)
        job = execute(qc, backend, shots = shots)
        result = job.result()
        counts = result.get_counts(qc)
        res_list.append(counts)
    return res_list
    
def get_fid(result_dir, origin_circuits_path, shots):
    hfs = {}
    real_results = get_res(result_dir)
#    print(real_results)
    sim_results = get_simulator_res(origin_circuits_path, shots)
    # print(sim_results)
    for i in range(len(real_results)):
        real_result = real_results[i]
        # print(real_result)
        sim_result = sim_results[i]
        # print(sim_result)
        hfs[origin_circuits_path[i]] = hellinger_fidelity(real_result, sim_result)
    return hfs

if __name__ == "__main__":
    qubit_num = 8
    y = {}
    x= {'00000000': 3176, '00000001': 917, '00010000': 36, '00010001': 9, '00010010': 1, '00010011': 4, '00010100': 12, '00010101': 1, '00010110': 9, '00010111': 16, '00011000': 28, '00011001': 11, '00011010': 5, '00011011': 8, '00011100': 28, '00011101': 12, '00011110': 34, '00011111': 22, '00000010': 268, '00100000': 215, '00100001': 72, '00100010': 16, '00100011': 7, '00100100': 5, '00100101': 3, '00100110': 2, '00100111': 4, '00101000': 17, '00101001': 5, '00101010': 3, '00101011': 1, '00101100': 7, '00101110': 10, '00101111': 5, '00000011': 125, '00110000': 42, '00110001': 10, '00110010': 12, '00110011': 5, '00110100': 12, '00110101': 4, '00110110': 8, '00110111': 13, '00111000': 34, '00111001': 7, '00111010': 7, '00111011': 4, '00111100': 34, '00111101': 19, '00111110': 33, '00111111': 36, '00000100': 140, '01000000': 142, '01000001': 51, '01000010': 10, '01000011': 3, '01000100': 12, '01000101': 2, '01000110': 4, '01000111': 1, '01001000': 9, '01001001': 2, '01001010': 1, '01001011': 2, '01001100': 3, '01001101': 2, '01001110': 5, '01001111': 5, '00000101': 60, '01010000': 20, '01010001': 5, '01010011': 1, '01010100': 2, '01010101': 2, '01010110': 5, '01010111': 2, '01011000': 11, '01011001': 3, '01011010': 2, '01011011': 6, '01011100': 10, '01011101': 7, '01011110': 16, '01011111': 13, '00000110': 44, '01100000': 32, '01100001': 9, '01100010': 1, '01100011': 1, '01100101': 4, '01100111': 2, '01101000': 8, '01101001': 3, '01101010': 4, '01101100': 3, '01101101': 3, '01101110': 4, '01101111': 10, '00000111': 41, '01110000': 78, '01110001': 25, '01110010': 7, '01110011': 5, '01110100': 14, '01110101': 5, '01110110': 17, '01110111': 17, '01111000': 40, '01111001': 8, '01111010': 7, '01111011': 6, '01111100': 57, '01111101': 21, '01111110': 29, '01111111': 47, '00001000': 198, '10000000': 364, '10000001': 98, '10000010': 29, '10000011': 17, '10000100': 22, '10000101': 7, '10000110': 9, '10000111': 7, '10001000': 39, '10001001': 15, '10001010': 6, '10001011': 6, '10001100': 15, '10001101': 3, '10001110': 13, '10001111': 14, '00001001': 74, '10010000': 22, '10010001': 6, '10010011': 2, '10010100': 2, '10010101': 1, '10010110': 3, '10010111': 3, '10011000': 9, '10011001': 3, '10011010': 2, '10011011': 2, '10011100': 14, '10011101': 7, '10011110': 11, '10011111': 16, '00001010': 27, '10100000': 48, '10100001': 15, '10100010': 10, '10100011': 2, '10100100': 4, '10100101': 1, '10100110': 2, '10100111': 2, '10101000': 10, '10101001': 2, '10101010': 2, '10101100': 8, '10101101': 4, '10101110': 6, '10101111': 5, '00001011': 19, '10110000': 39, '10110001': 11, '10110010': 6, '10110011': 2, '10110100': 15, '10110101': 4, '10110110': 8, '10110111': 13, '10111000': 20, '10111001': 4, '10111010': 4, '10111011': 8, '10111100': 33, '10111101': 7, '10111110': 22, '10111111': 31, '00001100': 38, '11000000': 372, '11000001': 97, '11000010': 28, '11000011': 8, '11000100': 11, '11000101': 6, '11000110': 2, '11000111': 4, '11001000': 18, '11001001': 8, '11001011': 3, '11001100': 8, '11001101': 2, '11001110': 8, '11001111': 8, '00001101': 16, '11010000': 39, '11010001': 6, '11010010': 9, '11010011': 5, '11010100': 8, '11010101': 7, '11010110': 14, '11010111': 12, '11011000': 21, '11011001': 10, '11011010': 9, '11011011': 8, '11011100': 50, '11011101': 21, '11011110': 45, '11011111': 37, '00001110': 31, '11100000': 139, '11100001': 41, '11100010': 14, '11100011': 4, '11100100': 7, '11100101': 2, '11100110': 7, '11100111': 6, '11101000': 25, '11101001': 6, '11101010': 4, '11101011': 3, '11101100': 17, '11101101': 8, '11101110': 12, '11101111': 10, '00001111': 31, '11110000': 138, '11110001': 42, '11110010': 18, '11110011': 13, '11110100': 42, '11110101': 19, '11110110': 47, '11110111': 40, '11111000': 100, '11111001': 41, '11111010': 28, '11111011': 23, '11111100': 134, '11111101': 65, '11111110': 110, '11111111': 157}
    y['0'*qubit_num] = 0.5
    y['1'*qubit_num] = 0.5
    print(hellinger_fidelity(x, y))