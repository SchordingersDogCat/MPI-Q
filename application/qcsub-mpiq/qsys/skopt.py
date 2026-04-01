import re
from skyline import Skyline  # 引入 skyline.py 的 Skyline 类

# -------------------------------
# 功能函数部分
# -------------------------------

def parse_qasm_file_for_shape(file_path, topology):    #
    """
    根据 QASM 文件确定量子比特的形状，并提取 QASM 文件内容。
    :param file_path: QASM 文件路径
    :param topology: 二维拓扑网格
    :return: 量子程序的形状矩阵和 QASM 文件内容
    """
    used_qubits = set()
    original_qasm = []

    # 解析 QASM 文件，提取量子寄存器和量子比特编号
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            original_qasm.append(line)  # 保存原始 QASM 指令
            if line.startswith("qreg"):
                match = re.match(r"qreg\s+q\[(\d+)\];", line)
                if match:
                    num_qubits = int(match.group(1))
                    used_qubits.update(range(num_qubits))

    # 将使用的量子比特映射到物理拓扑位置
    used_positions = []
    for row_idx, row in enumerate(topology):
        for col_idx, qubit in enumerate(row):
            if qubit in used_qubits:
                used_positions.append((row_idx, col_idx))

    # 生成形状矩阵
    shape = []
    if used_positions:
        current_row = used_positions[0][0]
        row_shape = []
        for pos in used_positions:
            row, col = pos
            if row != current_row:
                shape.append(row_shape)
                row_shape = []
                current_row = row
            row_shape.append(1)
        shape.append(row_shape)

    return shape, original_qasm

def parse_qasm_file_for_shape_new(qasm, topology):    #
    """
    根据 QASM 文件确定量子比特的形状，并提取 QASM 文件内容。
    :param file_path: QASM 文件路径
    :param topology: 二维拓扑网格
    :return: 量子程序的形状矩阵和 QASM 文件内容
    """
    used_qubits = set()
    original_qasm = []

    # 解析 QASM 文件，提取量子寄存器和量子比特编号
    # 按行分割字符串

    lines = qasm.strip().split('\n')

    

    # 打印每一行

    for line in lines:

        line = line.strip()
        original_qasm.append(line)  # 保存原始 QASM 指令
        if line.startswith("qreg"):
            match = re.match(r"qreg\s+q\[(\d+)\];", line)
            if match:
                num_qubits = int(match.group(1))
                used_qubits.update(range(num_qubits))

    # 将使用的量子比特映射到物理拓扑位置
    used_positions = []
    for row_idx, row in enumerate(topology):
        for col_idx, qubit in enumerate(row):
            if qubit in used_qubits:
                used_positions.append((row_idx, col_idx))

    # 生成形状矩阵
    shape = []
    if used_positions:
        current_row = used_positions[0][0]
        row_shape = []
        for pos in used_positions:
            row, col = pos
            if row != current_row:
                shape.append(row_shape)
                row_shape = []
                current_row = row
            row_shape.append(1)
        shape.append(row_shape)

    return shape, original_qasm

def process_multiple_qasm_files(qasm_files, topology):
    """
    处理多个 QASM 文件，生成“方块”格式队列。
    :param qasm_files: QASM 文件路径列表
    :param topology: 二维拓扑网格
    :return: 方块队列（shape, identifier, gates, original_qasm）
    """
    queue = []
    for idx, file_path in enumerate(qasm_files):
        shape, original_qasm = parse_qasm_file_for_shape(file_path[''], topology)
        fangkuai = {
            'shape': shape,
            'identifier': idx + 1,
            'gates': [],  # 当前默认为空，可以扩展为提取实际门信息
            'original_qasm': original_qasm  # 添加原始 QASM 内容
          
        }
        queue.append(fangkuai)
        # 输出单个方块的内容
        print(f"方块 {idx + 1} 的信息:")
        print(f"形状: {fangkuai['shape']}")
        print(f"标识符: {fangkuai['identifier']}")
        print(f"门信息: {fangkuai['gates']}")
        print(f"原始 QASM 内容: {fangkuai['original_qasm']}")

    # 输出整个队列的内容
    print("完整的方块队列:")
    print(queue)
    return queue

def process_multiple_qasm_files_new(qasm_list, topology):
    """
    处理多个 QASM 文件，生成“方块”格式队列。
    :param qasm_files: QASM 文件路径列表
    :param topology: 二维拓扑网格
    :return: 方块队列（shape, identifier, gates, original_qasm）
    """
    queue = []
    for idx, qasm_dict in enumerate(qasm_list):
        print('8888888888888888888888888888888888888888888')
        print(qasm_dict['id'])
        shape, original_qasm = parse_qasm_file_for_shape_new(qasm_dict['ir'], topology)
        fangkuai = {
            'shape': shape,
            'identifier': idx + 1,
            'gates': [],  # 当前默认为空，可以扩展为提取实际门信息
            'original_qasm': original_qasm,  # 添加原始 QASM 内容
            'id':qasm_dict['id']
        }
        queue.append(fangkuai)
        # 输出单个方块的内容
        print(f"方块 {idx + 1} 的信息:")
        print(f"形状: {fangkuai['shape']}")
        print(f"标识符: {fangkuai['identifier']}")
        print(f"门信息: {fangkuai['gates']}")
        print(f"原始 QASM 内容: {fangkuai['original_qasm']}")

    # 输出整个队列的内容
    print("完整的方块队列:")
    print(queue)
    return queue


def integrate_with_skyline(block_queue, width, height, max_height):
    """
    使用 Skyline 类对方块队列进行布局。
    :param block_queue: 从 QASM 文件生成的方块队列
    :param width: 棋盘宽度
    :param height: 棋盘高度
    :param max_height: 棋盘最大高度
    :return: 布局完成后的棋盘状态
    """
    # 初始化 Skyline 对象
    skyline = Skyline(width=width, height=height, max_height=max_height)

    # 遍历方块队列并尝试布局
    for block in block_queue:
        shape = block['shape']
        identifier = block['identifier']

        # 将方块传递给天际线布局
        success = skyline.update_with_adjustment(shape, identifier)
        if not success:
            raise ValueError(f"无法将方块 {identifier} 布局到棋盘中！")
    print("布局完成后的棋盘状态：")
    print(skyline.board)

    # 可视化布局结果
    #print("正在绘制布局结果...")
    #skyline.draw_board()  # 绘制棋盘
    # 返回布局结果
    return skyline.board, skyline




def calculate_creg_size(block_queue):
    """
    遍历所有 QASM 文件，计算 creg 的总大小。
    :param block_queue: 包含所有 QASM 文件内容的方块队列。
    :return: 所有文件中 creg 的总大小。
    """
    total_classical_bits = 0
    for block in block_queue:
        # 遍历每个方块的 QASM 文件，提取 creg 定义
        original_qasm = block.get("original_qasm", [])
        for line in original_qasm:
            if line.startswith("creg"):  # 查找 creg 定义
                match = re.match(r"creg\s+c\[(\d+)\];", line)
                if match:
                    block["creg_size"] = int(match.group(1))
                    total_classical_bits += block["creg_size"]
    return total_classical_bits


def generate_new_qasm_files(board, topology, block_queue, output_file):
    """
    根据棋盘布局和方块队列，更新 QASM 文件中的量子比特编号并合并成一个 QASM 文件。
    :param board: 布局后的棋盘状态，表示物理量子比特位置。
    :param topology: 二维拓扑网格，表示全局物理比特编号。
    :param block_queue: 方块队列，每个方块对应一个 QASM 文件的内容。
    :param output_file: 输出的合并 QASM 文件路径。
    """
    # 1. 预先计算 creg 的总大小
    total_classical_bits = calculate_creg_size(block_queue)

    # 2. 初始化 QASM 文件头
    total_qubits = 5  # 固定 qreg 为 
    merged_qasm = ["OPENQASM 2.0;", 'include "qelib1.inc";']
    merged_qasm.append(f"qreg q[{total_qubits}];")
    merged_qasm.append(f"creg c[{total_classical_bits}];")

    # 3. 遍历每个 block，根据棋盘位置和拓扑映射物理比特
    for identifier in range(1, len(block_queue) + 1):
        # 查找 block_queue 中的方块
        block = next((b for b in block_queue if b['identifier'] == identifier), None)
        if not block:
            print(f"警告：未找到标识符 {identifier} 对应的方块！")
            continue

        original_qasm = block.get("original_qasm", [])
        if not original_qasm:
            print(f"警告：标识符 {identifier} 的原始 QASM 内容为空！")
            continue

        # 获取棋盘上的物理比特位置
        physical_qubits = []
        for row_idx, row in enumerate(board):
            for col_idx, value in enumerate(row):
                if value == identifier:
                    # 从 topology 中获取物理比特编号
                    physical_qubits.append(topology[row_idx][col_idx])

        if not physical_qubits:
            print(f"警告：标识符 {identifier} 未找到任何物理比特位置！")
            continue

        # 更新 QASM 指令中的虚拟比特编号
        updated_qasm = []
        for line in original_qasm:
            # 跳过重复的头部内容
            if line.startswith("OPENQASM") or line.startswith("include"):
                continue
            if line.startswith("qreg") or line.startswith("creg"):
                continue  # 跳过寄存器定义
            updated_line = line
            for virtual_idx, physical_idx in enumerate(physical_qubits):
                updated_line = re.sub(rf"q\[{virtual_idx}\]", f"q[{physical_idx}]", updated_line)
            updated_qasm.append(updated_line)

        # 将更新后的指令添加到合并文件中
        merged_qasm.extend(updated_qasm)

    # 4. 写入合并的 QASM 文件
    if len(merged_qasm) > 4:  # 如果内容多于头部定义，说明有实际指令
        with open(output_file, "w") as f:
            f.write("\n".join(merged_qasm))
        print(f"新的 QASM 文件已保存到 {output_file}")
    else:
        print("错误：合并的 QASM 文件没有任何内容！")

def merge_qasm_lines(lines):
    # 使用换行符 '\n' 将列表中的每个元素连接成一个字符串
    merged_string = '\n'.join(lines)
    return merged_string
 


def generate_new_qasm_files_new(board, topology, block_queue, output_file):
    """
    根据棋盘布局和方块队列，更新 QASM 文件中的量子比特编号并合并成一个 QASM 文件。
    :param board: 布局后的棋盘状态，表示物理量子比特位置。
    :param topology: 二维拓扑网格，表示全局物理比特编号。
    :param block_queue: 方块队列，每个方块对应一个 QASM 文件的内容。
    :param output_file: 输出的合并 QASM 文件路径。
    """
    # 1. 预先计算 creg 的总大小
    total_classical_bits = calculate_creg_size(block_queue)
    print(f"total_classical_bits {total_classical_bits}")
    # 2. 初始化 QASM 文件头
    total_qubits = 5  # 固定 qreg 为 132
    merged_qasm = ["OPENQASM 2.0;", 'include "qelib1.inc";']
    merged_qasm.append(f"qreg q[{total_qubits}];")
    merged_qasm.append(f"creg c[{total_classical_bits}];")

    # 3. 遍历每个 block，根据棋盘位置和拓扑映射物理比特
    for identifier in range(1, len(block_queue) + 1):
        # 查找 block_queue 中的方块
        block = next((b for b in block_queue if b['identifier'] == identifier), None)
        if not block:
            print(f"警告：未找到标识符 {identifier} 对应的方块！")
            continue

        original_qasm = block.get("original_qasm", [])
        if not original_qasm:
            print(f"警告：标识符 {identifier} 的原始 QASM 内容为空！")
            continue

        # 获取棋盘上的物理比特位置
        physical_qubits = []
        for row_idx, row in enumerate(board):
            for col_idx, value in enumerate(row):
                if value == identifier:
                    # 从 topology 中获取物理比特编号
                    physical_qubits.append(topology[row_idx][col_idx])

        if not physical_qubits:
            print(f"警告：标识符 {identifier} 未找到任何物理比特位置！")
            continue

        # 更新 QASM 指令中的虚拟比特编号
        updated_qasm = []
        for line in original_qasm:
            # 跳过重复的头部内容
            if line.startswith("OPENQASM") or line.startswith("include"):
                continue
            if line.startswith("qreg") or line.startswith("creg"):
                continue  # 跳过寄存器定义
            updated_line = line
            for virtual_idx, physical_idx in enumerate(physical_qubits):
                updated_line = re.sub(rf"q\[{virtual_idx}\]", f"q[{physical_idx}]", updated_line)
            updated_qasm.append(updated_line)

        # 将更新后的指令添加到合并文件中
        merged_qasm.extend(updated_qasm)

    # 4. 写入合并的 QASM 文件
    if len(merged_qasm) > 4:  # 如果内容多于头部定义，说明有实际指令
        with open(output_file, "w") as f:
            f.write("\n".join(merged_qasm))
        print(f"新的 QASM 文件已保存到 {output_file}")
    else:
        print("错误：合并的 QASM 文件没有任何内容！")
    merged_qasm =  merge_qasm_lines(merged_qasm)

    return merged_qasm

def reorganize_measure_operations(input_file, output_file):
    """
    读取 QASM 文件，整理 measure 操作到文件末尾，并重新编号经典寄存器 c。
    :param input_file: 输入的 QASM 文件路径（如 merged_output.qasm）。
    :param output_file: 输出的 QASM 文件路径（如 end_output.qasm）。
    """
    with open(input_file, "r") as file:
        lines = file.readlines()

    # 初始化变量
    measure_instructions = []  # 存储所有 measure 指令
    other_instructions = []    # 存储非 measure 指令

    # 解析文件内容
    for line in lines:
        line = line.strip()
        # 检查是否为 measure 指令
        if line.startswith("measure"):
            measure_instructions.append(line)
        else:
            other_instructions.append(line)

    # 重新整理 measure 指令，经典寄存器编号从 0 开始
    reorganized_measure_instructions = []
    c_counter = 0  # 用于追踪经典寄存器 c 的编号
    for measure in measure_instructions:
        # 使用正则提取 measure 指令中的量子比特和经典比特编号
        match = re.match(r"measure\s+q\[(\d+)\]\s+->\s+c\[(\d+)\];", measure)
        if match:
            quantum_bit = match.group(1)  # 量子比特编号
            # 重新编号经典寄存器
            reorganized_measure_instructions.append(f"measure q[{quantum_bit}] -> c[{c_counter}];")
            c_counter += 1

    # 将整理后的内容写入输出文件
    with open(output_file, "w") as file:
        # 写入非 measure 指令
        for instruction in other_instructions:
            file.write(instruction + "\n")
        # 写入整理后的 measure 指令
        for instruction in reorganized_measure_instructions:
            file.write(instruction + "\n")

    print(f"整理后的 QASM 文件已保存到 {output_file}")

def reorganize_measure_operations_new(merge_qasm, output_file):
    """
    读取 QASM 文件，整理 measure 操作到文件末尾，并重新编号经典寄存器 c。
    :param input_file: 输入的 QASM 文件路径（如 merged_output.qasm）。
    :param output_file: 输出的 QASM 文件路径（如 end_output.qasm）。
    """
    # 按行分割字符串
    # print(merge_qasm)
    lines = merge_qasm.strip().split('\n')
    # print(lines)

    # 初始化变量
    measure_instructions = []  # 存储所有 measure 指令
    other_instructions = []    # 存储非 measure 指令

    # 解析文件内容
    for line in lines:
        line = line.strip()
        # 检查是否为 measure 指令
        if line.startswith("measure"):
            measure_instructions.append(line)
        else:
            other_instructions.append(line)

    # 重新整理 measure 指令，经典寄存器编号从 0 开始
    reorganized_measure_instructions = []
    c_counter = 0  # 用于追踪经典寄存器 c 的编号
    for measure in measure_instructions:
        # 使用正则提取 measure 指令中的量子比特和经典比特编号
        match = re.match(r"measure\s+q\[(\d+)\]\s+->\s+c\[(\d+)\];", measure)
        if match:
            quantum_bit = match.group(1)  # 量子比特编号
            # 重新编号经典寄存器
            reorganized_measure_instructions.append(f"measure q[{quantum_bit}] -> c[{c_counter}];")
            c_counter += 1

    # 将整理后的内容写入输出文件
    with open(output_file, "w") as file:
        # 写入非 measure 指令
        for instruction in other_instructions:
            file.write(instruction + "\n")
        # 写入整理后的 measure 指令
        for instruction in reorganized_measure_instructions:
            file.write(instruction + "\n")

    print(f"整理后的 QASM 文件已保存到 {output_file}")
    with open(output_file, "r") as file:
        lines = file.readlines()
    return lines

# 线路包装
def qasm_list_from_circ_list(circs):
    qasm_list = []
    # print("==================================")

    # print(circs)
    for circ in circs:
        qinit = circ['qinit']
        # real_ir = 'QINIT {0}\nCREG {0}\n'.format(qinit) + circ['ir'].replace(';', '\n').replace('Measure', 'MEASURE')
        real_ir = circ['ir']
        qasm_str=circ['ir']
        print("==================================")
        print(real_ir)
        print(qasm_str)
        #qasm_str = ld_quintengIR(real_ir)
        try:
            if 'measure' not in real_ir:
                circ_id = circ['id']
                quantum_task = QuantumTask.objects.get(id=circ_id)
                quantum_task.status = 5
                quantum_task.result = ''
                quantum_task.message = '没有添加测量门'
                quantum_task.save()
                ## 从缓存中剔除
                fld = circ['id']
                con = get_redis_connection('default')
                con.hdel(CONFIG.QUEUING_QUANTUM_TASK_CACHE, fld)
                continue
            # qasm转circ
            qc = QuantumCircuit.from_qasm_str(qasm_str)
            dag = circuit_to_dag(qc)
            path_depth = dag.depth()
            item_temp = {'id': circ['id'], 'name': circ['name'], 'qasm': qasm_str,
                         'path_depth': path_depth, 'shoots': 1000, 'num_qubits': qc.num_qubits, 'num_op': len(qc.data)}
            qasm_list.append(item_temp)
        except Exception as e:
            print(e)
            circ_id = circ['id']
            quantum_task = QuantumTask.objects.get(id=circ_id)
            quantum_task.status = 5
            quantum_task.result = ''
            quantum_task.message = '线路异常'
            quantum_task.save()
            ## 从缓存中剔除
            fld = circ['id']
            con = get_redis_connection('default')
            con.hdel(CONFIG.QUEUING_QUANTUM_TASK_CACHE, fld)
            continue
    return qasm_list

#####################记录每个文件的测量门个数
def calculate_measure_count(block_queue):
    """
    计算每个程序（标识符）中 measure 门的个数。
    :param block_queue: 包含所有 QASM 文件内容的方块队列。
    :return: 一个字典，键为标识符，值为该程序中的 measure 门个数。
    """
    measure_counts = {}  # 用于记录每个标识符的 measure 门个数

    for block in block_queue:
        identifier = block.get("id")  # 获取标识符
        original_qasm = block.get("original_qasm", [])  # 获取 QASM 内容

        # 统计 measure 指令的行数
        measure_count = sum(1 for line in original_qasm if line.strip().startswith("measure"))

        # 将标识符和对应的 measure 门个数记录到字典中
        measure_counts[identifier] = measure_count

    return measure_counts
#####################记录每个测量门测量了什么
def extract_measure_mapping(input_file):
    """
    从 QASM 文件中提取测量门的映射关系。
    :param input_file: 输入的 QASM 文件路径。
    :return: 一个二维数组，记录每个测量门的映射关系。
             第一维是测量门在 c[] 的顺序，
             第二维是该测量门对应的 q[]。
    """
    measure_mapping = []  # 用于记录二维数组，存储 c[] 和 q[] 的对应关系
    c_counter = 0  # 经典寄存器 c 的编号从 0 开始

    with open(input_file, "r") as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()
        # 检查是否为 measure 指令
        if line.startswith("measure"):
            # 使用正则表达式提取 measure 的 q[] 和 c[] 编号
            match = re.match(r"measure\s+q\[(\d+)\]\s+->\s+c\[(\d+)\];", line)
            if match:
                quantum_bit = int(match.group(1))  # 提取量子比特编号
                measure_mapping.append([c_counter, quantum_bit])  # 将 c[] 和 q[] 的关系记录到二维数组
                c_counter += 1  # 增加经典寄存器编号

    return measure_mapping
    
# -------------------------------
# 处理
# -------------------------------
def split_and_analyze_results(results, measure_counts):
    """
    根据程序的唯一标识符（measure_counts 的键）和测量门数量，对测量结果字典进行拆分和统计。

    :param results: 测量结果的字典，键为测量结果字符串，值为出现次数。
    :param measure_counts: 每个程序的测量门数量字典，键为程序标识符，值为该程序的测量门数量。
    :return: 一个字典，键为程序标识符，值为对应的测量结果统计。
    """
    # 初始化结果字典
    split_results = {}

    # 遍历每个程序的测量门数量
    current_start = 0  # 当前结果的起始索引
    for identifier, measure_count in measure_counts.items():
        split_results[identifier] = {}  # 为每个程序初始化结果字典

        # 遍历原始结果字典
        for result, count in results.items():
            # 按测量门数量截取结果
            truncated_result = result[current_start:current_start + measure_count]

            # 统计每个程序的测量结果
            if truncated_result not in split_results[identifier]:
                split_results[identifier][truncated_result] = 0
            split_results[identifier][truncated_result] += count

        # 更新起始索引
        current_start += measure_count

    return split_results

# -------------------------------
# 主函数
# -------------------------------
def skyline_opt(qasm_files):
    # 示例 QASM 文件路径列表
    # qasm_files = ["dj_4qubit.qasm", "dj_3qubit.qasm", "dj_41qubit.qasm", "dj_42qubit.qasm", "dj_43qubit.qasm"]  # 替换为实际文件路径

    # qasm_files=['''OPENQASM 2.0;
	# include "qelib1.inc";
	# qreg q[3];
	# creg c[2];
	# u2(0,pi) q[0];
	# x q[0];
	# u2(0,pi) q[1];
	# x q[1];
	# u3(pi,0,pi) q[2];
	# u2(0,pi) q[2];
	# cx q[0],q[2];
	# x q[0];
	# u2(0,pi) q[0];
	# cx q[1],q[2];
	# x q[1];
	# u2(0,pi) q[1];
	# barrier q[0],q[1],q[2];
	# measure q[0] -> c[0];
	# measure q[1] -> c[1];
	# ''','''OPENQASM 2.0;
	# include "qelib1.inc";
	# qreg q[4];
	# creg c[3];
	# u2(0,pi) q[0];
	# x q[0];
	# u2(0,pi) q[1];
	# x q[1];
	# u2(0,pi) q[2];
	# u3(pi,0,pi) q[3];
	# u2(0,pi) q[3];
	# cx q[0],q[3];
	# x q[0];
	# u2(0,pi) q[0];
	# cx q[1],q[3];
	# x q[1];
	# u2(0,pi) q[1];
	# cx q[2],q[3];
	# u2(0,pi) q[2];
	# barrier q[0],q[1],q[2],q[3];
	# measure q[0] -> c[0];
	# measure q[1] -> c[1];
	# measure q[2] -> c[2];''']

    # 示例 11×12 的网格拓扑
    topology = [
        [0, 1, 2, 3, 4]
    ]

    # 棋盘尺寸（与拓扑匹配）
    width, height, max_height = 5, 1, 1

    # 输出文件路径
    output_file = "merged_output.qasm"
    put_file = "end_output.qasm"
    # 处理 QASM 文件并生成方块队列

    block_queue = process_multiple_qasm_files_new(qasm_files, topology)

    # 将方块队列传递给 Skyline 进行布局
    board, skyline = integrate_with_skyline(block_queue, width, height, max_height)
    
    measure_counts = calculate_measure_count(block_queue)

    
    # 根据布局结果生成新的 QASM 文件
    merge_qasm = generate_new_qasm_files_new(board, topology, block_queue, output_file)

    out_qasm = reorganize_measure_operations_new(merge_qasm, put_file)
    out_qasm = ''.join(out_qasm)
    print(out_qasm)
    return out_qasm,measure_counts

#if __name__ == "__main__":
#    main()
