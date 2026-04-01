from pathlib import Path
import json
import copy
import os, re,subprocess
from circuit_knitting_toolbox.circuit_cutting.wire_cutting.muti_cut import reconstruct_cutqc_full
import shutil
import time
import numpy as np
import math
import sys
sys.path.append("..")
from utils.times import timer_decorator_env
from utils.print_utils import PCOLOR
import ast

pcolor = PCOLOR()

class superConfig():
    def __init__(self):
        self.SSH_PASS="s@FP1gw@qd@8"  # "XSFYMXEawK64heM"
        self.REMOTE_HOST="mscaosc@172.99.1.100" # "duqm@172.99.1.12"
        self.REMOTE_INPUT_PATH="/public/home/mscaosc/quan_parallel/subcirc_results_list"
        self.REMOTE_OUTPUT_PATH="/public/home/mscaosc/quan_parallel/reconstruct_result"
        self.REMOTE_SCRIPT_PATH="/public/home/mscaosc/quan_parallel/build"
        self.DCU_REMOTE_INPUT_PATH="/public/home/duqm/quan_parallel_dcu/subcirc_results_list"
        self.DCU_REMOTE_OUTPUT_PATH="/public/home/duqm/quan_parallel_dcu/reconstruct_result"
        self.DCU_REMOTE_SCRIPT_PATH="/public/home/duqm/quan_parallel_dcu"


def delete_files(directory, max_retries=5, retry_delay=2):
    """
    删除指定目录及其内容，支持重试机制以处理资源忙碌的情况。
    :param directory: 要删除的目录路径
    :param max_retries: 最大重试次数
    :param retry_delay: 每次重试之间的延迟（秒）
    """
    if not os.path.exists(directory):
        print(f"目录 {directory} 不存在，无需删除。")
        return

    for attempt in range(max_retries):
        try:
            shutil.rmtree(directory, ignore_errors=False)
            print(f"成功删除目录 {directory}")
            return
        except OSError as e:
            print(f"删除目录 {directory} 失败 (尝试 {attempt+1}/{max_retries})：{e}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数，仍然无法删除目录 {directory}")
                # 尝试逐个删除文件和子目录，忽略 NFS 锁定文件
                try:
                    for root, dirs, files in os.walk(directory, topdown=False):
                        for name in files:
                            file_path = os.path.join(root, name)
                            try:
                                if '.nfs' not in file_path:  # 跳过 NFS 临时文件
                                    os.remove(file_path)
                                    print(f"删除文件 {file_path} 成功")
                            except OSError as e2:
                                print(f"无法删除文件 {file_path}：{e2}")
                        for name in dirs:
                            dir_path = os.path.join(root, name)
                            try:
                                shutil.rmtree(dir_path, ignore_errors=True)
                                print(f"删除子目录 {dir_path} 成功")
                            except OSError as e2:
                                print(f"无法删除子目录 {dir_path}：{e2}")
                    print(f"尝试部分删除 {directory} 完成，可能仍有残留文件。")
                except Exception as e3:
                    print(f"部分删除失败：{e3}")


def has_multiple_folders(folder_path):
    # 获取指定文件夹路径下的所有内容
    contents = os.listdir(folder_path)

    # 过滤出文件夹（目录）并统计数量
    folders = [item for item in contents if os.path.isdir(os.path.join(folder_path, item))]

    # 判断文件夹数量是否大于1
    return len(folders) > 1

def delete_files(file_paths):
    """
    删除指定路径数组中的每个文件。
    :param file_paths: 包含文件路径的列表，每个路径对应的文件将被删除
    """
    directory = file_paths

    # 检查目录是否存在
    if os.path.exists(directory):
        # 删除目录及其内容
        shutil.rmtree(directory)

def read_folder_dicts(folder_path):
    # 获取文件夹中的所有子文件夹
    subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        # 按文件夹名称中的数字排序（如 subcircuit0, subcircuit1）
    subfolders.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
    print('=======子线路结果列表=======')
    print(subfolders)
    all_dicts = []  # 用于存放每个文件夹中的字典列表

    for subfolder in subfolders:
        subfolder_path = os.path.join(folder_path, subfolder)
        # print(subfolder_path)
        # 获取文件夹中的所有txt文件
        txt_files = [f for f in os.listdir(subfolder_path) if f.endswith('.txt')]
        # txt_files = [f.name for f in Path(subfolder_path).iterdir() if f.suffix.lower() == '.txt']
        
        # 按照文件名中的数字排序
        txt_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
        print(txt_files)
        
        folder_dicts = []  # 用于存放当前文件夹中的所有字典
        # print('x-x-x-x-x-x-x-x-x-x-')
        # 遍历所有txt文件
        for txt_file in txt_files:

            # print(f'txt_file:{txt_file}')
            txt_file_path = os.path.join(subfolder_path, txt_file)
            # print(f'txt_file_path:{txt_file_path}')
            # 读取文件内容并解析为字典
            # with open(txt_file_path, 'r', encoding='utf-8') as f:
            #     file_dict = json.load(f)  # 假设文件内容是JSON格式的字典
            #     folder_dicts.append(file_dict)
            # 读取文件内容
            with open(txt_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # 判断是否存在分隔符 ****
            has_separator = any(line.strip() == '****' for line in lines)
            
            # 提取数据
            data_lines = []
            for line in lines:
                stripped_line = line.strip()  # 去除首尾空白字符
                if has_separator and stripped_line == '****':
                    break  # 遇到第一个分隔符，停止读取
                if stripped_line:  # 忽略空行
                    data_lines.append(stripped_line)
            
            # delete_files(txt_file_path)
            # os.removedirs(subfolder_path)

            # 将数据转换为字典
            result_dict = {}
            for line in data_lines:
                key, value = line.split(':')
                result_dict[key.strip()] = float(value.strip())

            folder_dicts.append(result_dict)

        all_dicts.append(folder_dicts)

    return all_dicts

def read_folder_dicts_super(folder_path, apply_filter=False):
    """
    读取子线路结果并进行后处理。
    
    参数：
    - folder_path: str, 子线路结果文件夹路径。
    - apply_filter: bool, 是否应用筛选规则（取极大值或极小值），默认为 True。
    
    返回：
    - final_result: list, 处理后的结果列表。
    """
    # 获取所有subcircuit文件夹并按数字顺序排序
    subcircuit_folders = [f for f in os.listdir(folder_path) if f.startswith('subcircuit_') and os.path.isdir(os.path.join(folder_path, f))]
    subcircuit_folders.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    
    # 存储结果
    result = []

    # 上游部分：取subcircuit_0文件夹中的结果，按文件名顺序排序
    first_folder = subcircuit_folders[0] if subcircuit_folders else None
    first_group = []
    if first_folder:
        first_folder_path = os.path.join(folder_path, first_folder)
        if os.path.exists(first_folder_path):
            print(f"上游文件夹路径：{first_folder_path}")
            first_files = [f for f in os.listdir(first_folder_path) if f.endswith('_result.txt')]
            first_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
            for filename in first_files:
                file_path = os.path.join(first_folder_path, filename)
                data_dict = parse_file_to_dict(file_path)
                if data_dict:  # 仅在解析成功时添加
                    first_group.append(data_dict)
        else:
            print(f"上游文件夹不存在：{first_folder_path}")
    
    # 对上游结果进行筛选（如果启用）
    if apply_filter and first_group:
        first_group_filtered = []
        mes = ['I', 'Z', 'X', 'Y']
        for idx, res in enumerate(first_group):
            rev = True if mes[idx] in ['I', 'Z'] else False
            filtered_res = find_prob_events(res, check_high_prob=rev) if rev else find_low_prob(res)
            first_group_filtered.append(filtered_res)
        result.append(first_group_filtered)
    else:
        result.append(first_group)

    # 中间部分：处理subcircuit_1到subcircuit_(n-1)的文件夹，合并为一个二维列表
    middle_folders = subcircuit_folders[1:-1] if len(subcircuit_folders) > 2 else []
    middle_group = []
    for folder in middle_folders:
        folder_path_full = os.path.join(folder_path, folder)
        if not os.path.exists(folder_path_full):
            print(f"中间文件夹不存在：{folder_path_full}")
            continue
        
        print(f"中间文件夹路径：{folder_path_full}")
        middle_files = [f for f in os.listdir(folder_path_full) if f.endswith('_result.txt')]

        # 过滤掉带有执行次数后缀的文件（如 _1.txt, _2.txt），只保留第一次执行的结果
        middle_files = [f for f in middle_files if not re.search(r'_\d+\.txt$', f)]

        middle_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
        
        # 读取当前文件夹的所有结果
        current_folder_data = []
        for filename in middle_files:
            file_path = os.path.join(folder_path_full, filename)
            data_dict = parse_file_to_dict(file_path)
            if data_dict:  # 仅在解析成功时添加
                current_folder_data.append(data_dict)
        
        # 如果结果不足16个，取前4个进行复制，放到第二个子列表位置
        if len(current_folder_data) < 16:
            if len(current_folder_data) >= 4:
                first_four = current_folder_data[:4]
                while len(current_folder_data) < 16:
                    current_folder_data.append({})
                current_folder_data[4:8] = first_four
                print(f"中间文件夹 {folder} 结果不足16个(当前有 {len(current_folder_data) - (16 - len(middle_files))} 个),已复制前4个结果到第二个子列表位置")
            else:
                while len(current_folder_data) < 16:
                    current_folder_data.append({})
                print(f"中间文件夹 {folder} 结果不足4个(当前有 {len(middle_files)} 个),填充空字典到16个")
        
        # 对中间结果进行筛选（如果启用）
        if apply_filter:
            mes = ['I', 'Z', 'X', 'Y']
            filtered_data = []
            for idx in range(len(current_folder_data)):
                if idx < len(current_folder_data) and current_folder_data[idx]:
                    # 根据测量基决定筛选规则：I 和 Z 使用高概率筛选，X 和 Y 使用低概率筛选
                    base_idx = idx % len(mes)  # 测量基索引，循环对应 I, Z, X, Y
                    rev = True if mes[base_idx] in ['I', 'Z'] else False
                    filtered_res = find_prob_events(current_folder_data[idx], check_high_prob=rev) if rev else find_low_prob(current_folder_data[idx])
                    filtered_data.append(filtered_res)
                else:
                    filtered_data.append({})
            current_folder_data = filtered_data
        
        # 将当前文件夹的数据按每4个元素分组为一个子列表，形成二维列表
        current_group = []
        current_subgroup = []
        for i in range(len(current_folder_data)):
            if current_folder_data[i]:  # 仅添加非空字典
                current_subgroup.append(current_folder_data[i])
            if len(current_subgroup) == 4:
                middle_group.append(current_subgroup)
                current_subgroup = []
        if current_subgroup and len(current_subgroup) == 4:
            middle_group.append(current_subgroup)

    # 如果middle_group为空，初始化为空列表
    if not middle_group:
        middle_group = [[] for _ in range(4)]  # 确保有4个子列表以保持结构
    result.append(middle_group)

    # 下游部分：取最后一个subcircuit文件夹中的结果，按文件名顺序排序
    last_folder = subcircuit_folders[-1] if subcircuit_folders else None
    last_group = []
    if last_folder:
        last_folder_path = os.path.join(folder_path, last_folder)
        if os.path.exists(last_folder_path):
            print(f"下游文件夹路径：{last_folder_path}")
            last_files = [f for f in os.listdir(last_folder_path) if f.endswith('_result.txt')]
            last_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
            for filename in last_files:
                file_path = os.path.join(last_folder_path, filename)
                data_dict = parse_file_to_dict(file_path)
                if data_dict:  # 仅在解析成功时添加
                    last_group.append(data_dict)
        else:
            print(f"下游文件夹不存在：{last_folder_path}")

    # 对下游结果进行筛选（如果启用）
    if apply_filter and last_group:
        last_group_filtered = []
        init = ['0', '1', '+', 'i']
        for idx, res in enumerate(last_group):
            rev = True if init[idx] in ['0', '1'] else False
            filtered_res = find_prob_events(res, check_high_prob=rev) if rev else find_low_prob(res)
            last_group_filtered.append(filtered_res)
        last_group = last_group_filtered

    # 读取 JSON 文件中的复制规则
        # 读取 JSON 文件中的复制规则
    json_dir = os.path.join(os.path.dirname(__file__), '..', 'result', 'duplicate_info')
    json_file_path = os.path.join(json_dir, 'duplicates_info_cir_0.json')
    # 规范化路径以避免重复的 ./ 或其他问题
    json_file_path = os.path.normpath(json_file_path) 
    try:
        with open(json_file_path, 'r') as f:
            copy_rules = json.load(f)
        print(f"从 {json_file_path} 成功读取复制规则")
    except Exception as e:
        print(f"读取 JSON 文件失败：{e}")
        copy_rules = {}

    # 根据复制规则扩展 result 列表
    if copy_rules:  # 判断 JSON 是否非空
        max_index = max(int(idx) for idx in copy_rules.keys()) if copy_rules else len(result) - 1
        expanded_result = [[] for _ in range(max_index + 1)]
        expanded_result[0] = copy.deepcopy(result[0])  # 上游结果
        if len(result) > 1:
            expanded_result[1] = copy.deepcopy(result[1])  # 中间结果
        
        for target_idx, source_idx in copy_rules.items():
            target_idx = int(target_idx)
            source_idx = int(source_idx)
            if source_idx < len(expanded_result) and expanded_result[source_idx]:
                expanded_result[target_idx] = copy.deepcopy(expanded_result[source_idx])
                print(f"从索引 {source_idx} 复制到索引 {target_idx}")
            else:
                print(f"无法从索引 {source_idx} 复制到索引 {target_idx}，源数据为空或不存在")
        
        final_result = expanded_result + [copy.deepcopy(last_group)]
        print("已应用复制规则，生成扩展结果，并将下游结果放在最后位置")
    else:
        final_result = copy.deepcopy(result)
        if final_result and final_result[-1] != last_group:
            final_result.append(copy.deepcopy(last_group))
        elif not final_result:
            final_result = [copy.deepcopy(last_group)]
        print("JSON 为空，未应用复制规则，使用原始结果，并将下游结果放在最后位置")

    return final_result

def duplicate_results_based_on_info(results, duplicates_info):
    if not results or not duplicates_info:
        return results
    import copy

    # 安全解析 duplicates_info：确保 key 和 value 都是整数
    copy_map = {}
    for k, v in duplicates_info.items():
        try:
            target = int(k)
            source = int(v)
            copy_map[target] = source
        except (ValueError, TypeError):
            print(f"警告：跳过无效复制规则 {k}: {v}")
            continue

    if not copy_map:
        return results
    # print(f"复制规则: {copy_map}")
    # print(f"结果:{results}")
    upstream = results[0]
    downstream =results[-1]
    # print(f"下游结果:{downstream}")
    # 确定最大目标索引
    max_target = max(copy_map.keys())

    # 构建最终结果
    final_result = [upstream]

    # 填充索引 1 到 max_target
    for idx in range(1, max_target + 1):
        if idx in copy_map:
            source_idx = copy_map[idx]
            if 0 <= source_idx < len(results):
                final_result.append(copy.deepcopy(results[source_idx]))
            else:
                final_result.append([])  # 源索引无效
        else:
            # 如果没有复制规则，且原始有对应中间内容，则保留
            if 1 <= idx < len(results) - 1:
                final_result.append(copy.deepcopy(results[idx]))
            else:
                final_result.append([])

    # 添加最后一个（下游）
    final_result.append(downstream)

    return final_result

def read_subcircuit_results(base_folder, filter_func=None):
    """
    从子线路结果文件夹中读取数据，并整理为二维列表格式。
    
    参数:
        base_folder (str): 子线路结果的根目录，包含多个子线路文件夹（如 sub0, sub1, ...）。
        filter_func (callable, optional): 筛选函数，输入 tag，返回是否保留该结果。默认为 None，表示不筛选。
    
    返回:
        list: 二维列表 [[(tag, counts_dict), ...], [(tag, counts_dict), ...], ...]，
              每个子列表对应一个子线路路径下的结果。
    """
    # 获取所有子线路文件夹（假设文件夹名为 sub0, sub1, ...）
    # sub_dirs = sorted(
    #     [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d)) and d.startswith('subcircuit')],
    #     key=lambda x: int(x.replace('subcircuit', ''))
    # )
    
    sub_dirs = sorted(
            [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d)) and d.startswith('subcircuit')],
            key=lambda x: int(x.replace('subcircuit_', ''))
        )
    
    #print(sub_dirs)
    # 存储所有子线路的结果
    all_sub_results = []
    
    # 遍历每个子线路文件夹
    for sub_dir in sub_dirs:
        
        sub_path = os.path.join(base_folder, sub_dir)
        sub_results = []
        
        # 遍历子线路文件夹中的每个结果文件
        for filename in os.listdir(sub_path):
            if filename.endswith('_result.txt'):  # 假设结果文件以 _result.txt 结尾
                if re.search(r'_\d+\.txt$', filename):
                    continue
                file_path = os.path.join(sub_path, filename)
                tag = decode_tag_from_filename(filename)
                
                # 应用筛选函数（如果有）
                if filter_func and not filter_func(tag):
                    continue
                
                # 读取文件内容并解析为概率分布字典
                counts_dict = parse_file_to_dict(file_path)
                sub_results.append((tag, counts_dict))
        
        # 将当前子线路的结果添加到总列表
        all_sub_results.append(sub_results)
         # 读取 JSON 文件中的复制规则
    json_dir = os.path.join(os.path.dirname(__file__), '..', 'result', 'duplicate_info')
    #####后面这里要修改，不能写死
    json_file_path = os.path.join(json_dir, 'duplicates_info_cir_0.json')
    # 规范化路径以避免重复的 ./ 或其他问题
    json_file_path = os.path.normpath(json_file_path) 
    try:
        with open(json_file_path, 'r') as f:
            copy_rules = json.load(f)
        print(f"从 {json_file_path} 成功读取复制规则")
    except Exception as e:
        print(f"读取 JSON 文件失败：{e}")
        copy_rules = {}
    
    duplicated_results = duplicate_results_based_on_info(
                all_sub_results, copy_rules
            )

    return duplicated_results

def decode_tag_from_filename(filename):
    """
    从新文件名格式（如 result_trans_sub2_+_none.txt）中解析 tag。
    返回值示例：('+', 'none')
    """
    # 1. 去除扩展名
    name_without_ext = filename.split("_result.txt")[0]
    
    # 2. 分割下划线并提取最后两个元素
    parts = name_without_ext.split("_")
    return tuple(parts[-2:])  # 直接取最后两个部分



def parse_file_to_dict(file_path):
    """
    读取文件内容并直接解析为字典格式
    
    参数：
    - file_path: str, 文件路径
    
    返回：
    - result_dict: dict, 直接返回文件中的字典
    """
    try:
        with open(file_path, 'r') as f:
            # 读取整个文件内容
            file_content = f.read().strip()
            
            # 使用安全解析将字符串转为字典
            result_dict = ast.literal_eval(file_content)
            # result_dict = {k: int(v * 8192) for k, v in result_dict.items()}
            # 确保返回的是字典类型
            if not isinstance(result_dict, dict):
                raise ValueError("文件内容不是字典格式")
                
            return result_dict
            
    except Exception as e:
        print(f"文件 {file_path} 解析失败：{e}")
        return {}


# 筛选函数：寻找低概率事件
def find_low_prob(data, coef=0.2):
    total_sum = sum(data.values())
    sorted_counts = sorted(data.items(), key=lambda x: x[1], reverse=False)
    length = math.ceil(len(sorted_counts) * coef)
    top_counts = dict(sorted_counts[:length])
    top_result = {key: value / total_sum for key, value in top_counts.items()}
    return top_result

# 筛选函数：根据相对偏差筛选高概率或低概率事件
def find_prob_events(data, check_high_prob=True, deviation_threshold=0.4):
    total_count = sum(data.values())
    probabilities = np.array(list(data.values())) / total_count
    keys = list(data.keys())
    mean_prob = np.mean(probabilities)
    if check_high_prob:
        events = {k: p for k, p in zip(keys, probabilities) if p >= mean_prob * (1 + deviation_threshold)}
    else:
        events = {k: p for k, p in zip(keys, probabilities) if p <= mean_prob * (1 - deviation_threshold)}
    return events if events else {k: v / total_count for k, v in data.items()}

@timer_decorator_env()
def reconstruct_cutqc(currentPath, parallel_result_path, local_log_path,
                      cuts_list:None,
                      cut_order_list:None,
                      cut_position_list:None,
                      cut_method:None,
                      supercomputing:None,
                      super_nodes:None,
                      dcu:None):
    """

    编译并运行 five_tupo_renyi.cpp 程序，并传递 currentPath 和 parallel_result_path作为参数。

    参数:
    currentPath (str): 当前路径参数。
    parallel_result_path (str): 基础路径参数。
    """
    os.makedirs(f'{local_log_path}', exist_ok=True)
    print("currentPath:", currentPath)
    # 是否使用超算
    if supercomputing == True:
        try:
            delete_files(f'{parallel_result_path}/super_result/')
        except Exception as e:
            print(f"删除 super_result 目录失败，但程序将继续执行：{e}")
        os.makedirs(f'{parallel_result_path}/super_result/', exist_ok=True)
        items = os.listdir(currentPath)
        circuit_path_items = [item for item in items if os.path.isdir(os.path.join(currentPath, item))]

        circuit_l1_result = []
        for idx, circuit_paths_item in enumerate(circuit_path_items):
            
            start_1 = time.perf_counter()
            circuit_path = os.path.join(currentPath, circuit_paths_item)
            # print(circuit_path)
            if has_multiple_folders(circuit_path):
                subcir_result = read_subcircuit_results(circuit_path)  #read_folder_dicts_super
                circuit_l1_result.append(subcir_result)
            os.makedirs(f'{parallel_result_path}/super_result/circuit{idx}', exist_ok=True)
            
            # step1: 汇总子线路运行结果
            with open(f'{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_subcir_result.txt','w') as f:
                f.write(str(subcir_result))
            end_1 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 1 耗时: {end_1-start_1:.3f} s {pcolor.RESET}")
            
            
            # step2: 向远程机器发送子线路结果
            superconf = superConfig()
            
            start_2 = time.perf_counter()
            if dcu:
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "scp", "-o", "StrictHostKeyChecking=no",
                            f"{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_subcir_result.txt", 
                            f"{superconf.REMOTE_HOST}:{superconf.DCU_REMOTE_INPUT_PATH}"
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_subcir_result.txt 文件已成功发送到远程主机")
                except subprocess.CalledProcessError as e:
                    print(f"传输失败，错误信息：{e.stderr.decode().strip()}")
            else:
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "scp", "-o", "StrictHostKeyChecking=no",
                            f"{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_subcir_result.txt", 
                            f"{superconf.REMOTE_HOST}:{superconf.REMOTE_INPUT_PATH}"
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_subcir_result.txt 文件已成功发送到远程主机")
                except subprocess.CalledProcessError as e:
                    print(f"传输失败，错误信息：{e.stderr.decode().strip()}")
            
            end_2 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 2 耗时: {end_2-start_2:.3f} s {pcolor.RESET}")
            
            # 是否使用dcu
            if dcu:
                script_info = rf'''#!/bin/bash   
#SBATCH --job-name=test_quan_parallel_10_500_DCU   
#SBATCH --nodes=5 #节点数
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32 
#SBATCH --gres=dcu:4
#SBATCH --mem=100G  

#SBATCH -p xinda  #作业队列
#SBATCH -o %j.log
#SBATCH -e %j.log

export OMPI_MCA_pml=ucx           # 使用 UCX 传输层
export OMPI_MCA_btl=^openib       # 禁用 openib BTL(若使用 UCX)

#SBATCH --exclusive # 设置独占节点

module purge

module load compiler/gcc/11.2.0
module load compiler/rocm/dtk-23.04
module load mpi/intelmpi/2021.3.0
module load compiler/cmake/3.28.0

export I_MPI_PMI_LIBRARY=/opt/gridview/slurm/lib/libpmi.so
export I_MPI_STATS=10
export I_MPI_TRACE=1
export I_MPI_TUNING=full

export CC=/public/software/compiler/rocm/dtk-23.04/bin/hipcc
export CXX=/public/software/compiler/rocm/dtk-23.04/bin/hipcc

cd {superconf.DCU_REMOTE_SCRIPT_PATH}
# running the command
rm -rf build
mkdir build
cd build

# 设置 CMake 编译选项
export CMAKE_CXX_FLAGS="-fgpu-rdc -std=c++17 -stdlib=libstdc++ -I$ROCM_PATH/include"
export CMAKE_EXE_LINKER_FLAGS="$CMAKE_EXE_LINKER_FLAGS -lstdc++fs"

cmake ..
make

echo "SLURM_JOB_PARTITION=$SLURM_JOB_PARTITION" 
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST" 

# 运行程序并传递输入和输出路径作为参数
srun --mpi=pmix_v3 ./five_tupo_renyi_dcu --input {superconf.DCU_REMOTE_INPUT_PATH}/circuit{idx}_subcir_result.txt --output {superconf.DCU_REMOTE_OUTPUT_PATH}/circuit{idx}_reconstruct_result.txt
'''
            else:
                script_info = rf'''#!/bin/bash  
#SBATCH --job-name=test_quan_parallel   
#SBATCH --nodes={super_nodes} #节点数
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32 
#SBATCH --mem=200G  

#SBATCH -p  xinda #作业队列 ccf_jingdian
#SBATCH -o %j.log
#SBATCH -e %j.log

#SBATCH --exclusive # 设置独占节点

export OMP_NUM_THREADS="32,32"

echo "SLURM_JOB_PARTITION=$SLURM_JOB_PARTITION" 

echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST" 

# 运行程序并传递输入和输出路径作为参数
srun --mpi=pmix_v3 ./five_tupo_renyi --input {superconf.REMOTE_INPUT_PATH}/circuit{idx}_subcir_result.txt --output {superconf.REMOTE_OUTPUT_PATH}/circuit{idx}_reconstruct_result.txt
'''
            # step3: 生成超算作业提交脚本到本地
            start_3 = time.perf_counter()
            with open(f'{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_script.sh','w') as f:
                f.write(script_info)
            end_3 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 3 耗时: {end_3-start_3:.3f} s {pcolor.RESET}")
            # step4: 将超算作业提交脚本发送至远程作业提交节点
            start_4 = time.perf_counter()
            if dcu:
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "scp", "-o", "StrictHostKeyChecking=no",
                            f"{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_script.sh", 
                            f"{superconf.REMOTE_HOST}:{superconf.DCU_REMOTE_SCRIPT_PATH}"
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_script.sh 文件已成功发送到远程主机")
                except subprocess.CalledProcessError as e:
                    print(f"传输失败，错误信息：{e.stderr.decode().strip()}")                
            else: 
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "scp", "-o", "StrictHostKeyChecking=no",
                            f"{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_script.sh", 
                            f"{superconf.REMOTE_HOST}:{superconf.REMOTE_SCRIPT_PATH}"
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_script.sh 文件已成功发送到远程主机")
                except subprocess.CalledProcessError as e:
                    print(f"传输失败，错误信息：{e.stderr.decode().strip()}")
            end_4 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 4 耗时: {end_4-start_4:.3f} s {pcolor.RESET}")
            
            # step5: 清空远程作业提交节点的重构文件避免误检
            start_5 = time.perf_counter()
            if dcu:
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "ssh",
                            f"{superconf.REMOTE_HOST}",
                            f'cd {superconf.DCU_REMOTE_OUTPUT_PATH} && test -f circuit{idx}_reconstruct_result.txt && rm -f circuit{idx}_reconstruct_result.txt'
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_reconstruct_result.txt 旧文件存在已删除")
                except subprocess.CalledProcessError as e:
                    print(f"清空远程作业提交节点的重构文件，错误信息：{e.stderr.decode().strip()}")   
            else:   
                try:
                    subprocess.run(
                        [
                            "sshpass", "-p", superconf.SSH_PASS,
                            "ssh",
                            f"{superconf.REMOTE_HOST}",
                            f'cd {superconf.REMOTE_OUTPUT_PATH} && test -f circuit{idx}_reconstruct_result.txt && rm -f circuit{idx}_reconstruct_result.txt'
                        ],
                        check=True,  # 如果命令失败会抛出异常
                        stderr=subprocess.PIPE  # 捕获错误输出
                    )
                    print(f"circuit{idx}_reconstruct_result.txt 旧文件存在已删除")
                except subprocess.CalledProcessError as e:
                    print(f"清空远程作业提交节点的重构文件，错误信息：{e.stderr.decode().strip()}")   
                    
            end_5 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 5 耗时: {end_5-start_5:.3f} s {pcolor.RESET}")        
            
            
            # step6: 生成远程执行脚本到本地
            if dcu:
                remote_and_return = rf'''#!/bin/bash
# 远程服务器信息
REMOTE_HOST="{superconf.REMOTE_HOST}"      # 替换为远程服务器的用户名和IP地址
REMOTE_SCRIPT_PATH={superconf.DCU_REMOTE_SCRIPT_PATH}    # 替换为远程服务器上a.sh的完整路径
REMOTE_SCRIPT="circuit{idx}_script.sh"
REMOTE_FILE_PATH="{superconf.DCU_REMOTE_OUTPUT_PATH}/circuit{idx}_reconstruct_result.txt"  # 替换为远程服务器上生成的文件路径
LOCAL_JOB_STATUS="{parallel_result_path}/super_result/circuit{idx}/circuit_{idx}_job_status.txt"               # 本地保存脚本执行输出的文件名
LOCAL_FILE_PATH="{parallel_result_path}/super_result/circuit{idx}/circuit_{idx}_reconstruct_result.txt"      # 本地保存远程生成文件的路径
SSH_PASS="{superconf.SSH_PASS}"

# 检查是否安装了sshpass(如果需要自动输入密码)
if ! command -v sshpass &> /dev/null; then
    echo "sshpass 未安装，请先安装 sshpass"
    echo "在Ubuntu上可以使用: sudo apt-get install sshpass"
    echo "在CentOS上可以使用: sudo yum install sshpass"
    exit 1
fi

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%H:%M:%S.%f")[:-3])')"

# 使用SSH登录远程服务器并执行脚本,将结果保存到本地
echo "正在连接远程服务器并执行脚本..."
# 如果使用密码登录(需要安装sshpass)

sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST" "cd $REMOTE_SCRIPT_PATH && sbatch $REMOTE_SCRIPT" > "$LOCAL_JOB_STATUS" 2>&1

cat $LOCAL_JOB_STATUS

JOB_ID=$(grep -oE '[0-9]+$' "$LOCAL_JOB_STATUS")

REMOTE_LOG_PATH="{superconf.DCU_REMOTE_SCRIPT_PATH}/${{JOB_ID}}.log"
LOCAL_LOG_PATH="{local_log_path}/${{JOB_ID}}.log"


# SSH检测函数
# check_remote_file() {{
#     sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST"  "cd ~/. && bash -c '[[ -f \"${{REMOTE_FILE_PATH}}\" ]] && echo exist || echo not found'"
# }}

check_remote_file() {{
    sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST" \
    "if [[ -f \"${{REMOTE_FILE_PATH}}\" ]]; then 
        echo \"exist \$(stat -c%s \"${{REMOTE_FILE_PATH}}\")\"
     else 
        echo 'not_found 0'
     fi"
}}

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%H:%M:%S.%f")[:-3])')"

# 检查脚本执行是否成功
if [ $? -eq 0 ]; then
    echo "脚本执行成功"
    # 主监控循环
    echo "🔍 开始监控远程文件:"
    START_TIME=$(date +%s)
    CHECK_INTERVAL=${{5:-0.5}}
    TIMEOUT=${{6:-5000}}
    while true; do
        # 超时检测
        CURRENT_TIME=$(date +%s)
        if (( CURRENT_TIME - START_TIME > TIMEOUT )); then
            TIMEOUT_FLAG=1
            break
        fi

        # 执行远程检测
        read -r RESULT FILE_SIZE <<< "$(check_remote_file)"
        echo "$(check_remote_file)"

        if [ "$RESULT" == "exist" ]; then
            echo -e "\n 检测到结果文件 (大小: ${{FILE_SIZE}}字节)"
            break
        else
            # 动态进度显示
            ELAPSED=$((CURRENT_TIME - START_TIME))
            printf "\r⌛ 等待中 [%03d/%03d秒] " "$ELAPSED" "$TIMEOUT"
            sleep "$CHECK_INTERVAL"
        fi
    done
    echo "执行结果已保存到 $REMOTE_FILE_PATH"

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%H:%M:%S.%f")[:-3])')"

else
    echo "脚本执行失败，请检查错误信息："
    cat "$REMOTE_FILE_PATH"
    exit 1
fi

# 使用SCP将远程服务器生成的文件回传到本地
echo "正在回传远程服务器生成的文件..."
# 如果使用密码登录(需要安装sshpass)
sshpass -p "$SSH_PASS" scp -o "StrictHostKeyChecking=no" "$REMOTE_HOST:$REMOTE_FILE_PATH" "$LOCAL_FILE_PATH"

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%H:%M:%S.%f")[:-3])')"

# 如果使用SSH密钥登录(不需要sshpass)
# scp -o "StrictHostKeyChecking=no" "$REMOTE_HOST:$REMOTE_FILE_PATH" "$LOCAL_FILE_PATH"

# 检查文件回传是否成功
if [ $? -eq 0 ]; then
    echo "文件回传成功，保存到本地路径: $LOCAL_FILE_PATH"
else
    echo "文件回传失败，请检查远程文件路径是否正确或是否有权限"
    exit 1
fi'''
            else:
                remote_and_return = rf'''#!/bin/bash
# 远程服务器信息
REMOTE_HOST="{superconf.REMOTE_HOST}"      # 替换为远程服务器的用户名和IP地址
REMOTE_SCRIPT_PATH={superconf.REMOTE_SCRIPT_PATH}    # 替换为远程服务器上a.sh的完整路径
REMOTE_SCRIPT="circuit{idx}_script.sh"
REMOTE_FILE_PATH="{superconf.REMOTE_OUTPUT_PATH}/circuit{idx}_reconstruct_result.txt"  # 替换为远程服务器上生成的文件路径
LOCAL_JOB_STATUS="{parallel_result_path}/super_result/circuit{idx}/circuit_{idx}_job_status.txt"               # 本地保存脚本执行输出的文件名
LOCAL_FILE_PATH="{parallel_result_path}/super_result/circuit{idx}/circuit_{idx}_reconstruct_result.txt"      # 本地保存远程生成文件的路径
SSH_PASS="{superconf.SSH_PASS}"



# 检查是否安装了sshpass(如果需要自动输入密码)
if ! command -v sshpass &> /dev/null; then
    echo "sshpass 未安装，请先安装 sshpass"
    echo "在Ubuntu上可以使用: sudo apt-get install sshpass"
    echo "在CentOS上可以使用: sudo yum install sshpass"
    exit 1
fi

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])')"

# 使用SSH登录远程服务器并执行脚本,将结果保存到本地
echo "正在连接远程服务器并执行脚本..."
# 如果使用密码登录(需要安装sshpass)

sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST" "module purge && module load compiler/devtoolset/7.3.1 mpi/hpcx/2.11.0/gcc-7.3.1 compiler/cmake/3.28.0 && cd $REMOTE_SCRIPT_PATH && sbatch $REMOTE_SCRIPT" > "$LOCAL_JOB_STATUS" 2>&1  

cat $LOCAL_JOB_STATUS

JOB_ID=$(grep -oE '[0-9]+$' "$LOCAL_JOB_STATUS")

REMOTE_LOG_PATH="{superconf.REMOTE_SCRIPT_PATH}/${{JOB_ID}}.log"
LOCAL_LOG_PATH="{local_log_path}/${{JOB_ID}}.log"

# SSH检测函数
# check_remote_file() {{
#     sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST"  "cd ~/. && bash -c '[[ -f \"${{REMOTE_FILE_PATH}}\" ]] && echo exist || echo not found'"
# }}

check_remote_file() {{
    sshpass -p "$SSH_PASS" ssh -o "StrictHostKeyChecking=no" "$REMOTE_HOST" \
    "if [[ -f \"${{REMOTE_FILE_PATH}}\" ]]; then 
        echo \"exist \$(stat -c%s \"${{REMOTE_FILE_PATH}}\")\"
     else 
        echo 'not found'
     fi"
}}

# 检查脚本执行是否成功
if [ $? -eq 0 ]; then
    echo "脚本执行成功"
    # 主监控循环
    echo "🔍 开始监控远程文件:"
    START_TIME=$(date +%s)
    CHECK_INTERVAL=${{5:-0.5}}
    TIMEOUT=${{6:-5000}}
    while true; do
        # 超时检测
        CURRENT_TIME=$(date +%s)
        if (( CURRENT_TIME - START_TIME > TIMEOUT )); then
            TIMEOUT_FLAG=1
            break
        fi

        # 执行远程检测
        read -r RESULT FILE_SIZE <<< "$(check_remote_file)"
        echo "$(check_remote_file)"

        if [ "$RESULT" == "exist" ]; then
            echo -e "\n✅ 检测到结果文件 (大小: $(numfmt --to=iec ${{FILE_SIZE}}))"
            break
        else
            # 动态进度显示
            ELAPSED=$((CURRENT_TIME - START_TIME))
            printf "\r⌛ 等待中 [%03d/%03d秒] " "$ELAPSED" "$TIMEOUT"
            sleep "$CHECK_INTERVAL"
        fi
    done
    echo "执行结果已保存到 $REMOTE_FILE_PATH"

else
    echo "脚本执行失败，请检查错误信息："
    cat "$REMOTE_FILE_PATH"
    exit 1
fi

# 使用SCP将远程服务器生成的文件回传到本地
echo "正在回传远程服务器生成的文件..."

# 如果使用密码登录(需要安装sshpass)
sshpass -p "$SSH_PASS" scp -o "StrictHostKeyChecking=no" "$REMOTE_HOST:$REMOTE_FILE_PATH" "$LOCAL_FILE_PATH"
sshpass -p "$SSH_PASS" scp -o "StrictHostKeyChecking=no" "$REMOTE_HOST:$REMOTE_LOG_PATH" "$LOCAL_LOG_PATH"

# 如果使用SSH密钥登录(不需要sshpass)
# scp -o "StrictHostKeyChecking=no" "$REMOTE_HOST:$REMOTE_FILE_PATH" "$LOCAL_FILE_PATH"

echo "Now: $(python -c 'from datetime import datetime; print(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])')"

# 检查文件回传是否成功
if [ $? -eq 0 ]; then
    echo "文件回传成功，保存到本地路径: $LOCAL_FILE_PATH"
    echo "文件回传成功，保存到本地路径: $LOCAL_LOG_PATH"

else
    echo "文件回传失败，请检查远程文件路径是否正确或是否有权限"
    exit 1
fi'''
            
            start_6 = time.perf_counter()
            with open(f'{parallel_result_path}/super_result/circuit{idx}/circuit{idx}_remote_execute.sh','w') as f:
                f.write(remote_and_return)
            end_6 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 6 耗时: {end_6-start_6:.3f} s {pcolor.RESET}")
            
            
            # step7: 本地执行脚本
            # step7.1：登录作业提交节点并运行作业提交脚本
            # step7.2：检测重构任务是否完成，即目标文件是否已生成
            # step7.3：若已生成，则回传到本地
            start_7 = time.perf_counter()
            try:
                subprocess.run(
                    [
                        f"bash -i {parallel_result_path}/super_result/circuit{idx}/circuit{idx}_remote_execute.sh", 
                    ],
                    check=True,  # 如果命令失败会抛出异常
                    shell=True,
                    stderr=subprocess.PIPE  # 捕获错误输出
                )
                #print(f"计算结果已回传至本机: {parallel_result_path}/super_result/circuit{idx}/circuit_{idx}_reconstruct_result.txt")
            except subprocess.CalledProcessError as e:
                print(f"传输失败，错误信息：{e.stderr.decode().strip()}")
                           
            end_7 = time.perf_counter()
            print(f"{pcolor.RED_BOLD}[TIMER] reconstruct_cutqc step 7 耗时: {end_7-start_7:.3f} s {pcolor.RESET}")
                           
            # file_path = f'{parallel_result_path}/reconstruct_result/circuit{idx}/result_rec.txt'
                  
        
        # file_path = f'{parallel_result_path}/reconstruct_result/circuit{idx}/result_rec.txt'
        # # 检查路径是否存在，如果不存在则创建
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
    # 不使用超算重构即在本机进行重构
    else: 
        items = os.listdir(currentPath)
        circuit_path_items = [item for item in items if os.path.isdir(os.path.join(currentPath, item))]
        circuit_path_items.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
        # print(circuit_path_items)

        try:
            delete_files(f'{parallel_result_path}/local_sub_result')
            delete_files(f'{parallel_result_path}/local_reconstruct_result')
        except Exception as e:
            print(f"删除 {parallel_result_path}/local_reconstruct_result, {parallel_result_path}/local_reconstruct_result 目录失败，但程序将继续执行：{e}")
        for idx, circuit_paths_item in enumerate(circuit_path_items):
            circuit_path = os.path.join(currentPath, circuit_paths_item)
            
            # 判断是否为全连接线路，即根据目录下是否有多个子目录来判断
            if has_multiple_folders(circuit_path):
                
                subcir_result = read_subcircuit_results(circuit_path)
                print(subcir_result)

                # 获取子线路结果文件路径，汇总，并赋值给 result_subcir_path
                result_subcir_path = os.path.join(
                    parallel_result_path,
                    "local_sub_result",
                    f"circuit{idx}",
                    f"circuit{idx}_subcir_result.txt"
                )

                # 创建目录并写入结果文件
                os.makedirs(os.path.dirname(result_subcir_path), exist_ok=True)
                with open(result_subcir_path, 'w') as f:
                    f.write(str(subcir_result))

                # 存放最终重构结果文件路径，并赋值给 reconstruct_result_path
                reconstruct_result_path = os.path.join(
                    parallel_result_path,
                    "local_reconstruct_result",
                    f"circuit{idx}",
                    f"circuit{idx}_reconstruct_result.txt"
                )

                # 创建目录并写入结果文件
                os.makedirs(os.path.dirname(reconstruct_result_path), exist_ok=True)

                if cut_method == "automatic":
                    # python本地重构
                    
                    init = ['0', '1', '+', 'i']
                    mes = ['I', 'Z', 'X', 'Y'] # Match file extensions
                    pA, pB = [], []
                    #print(subcir_result)
                    for up in mes:
                        for items in subcir_result:
                            for item in items:
                                # item[0] is metadata tuple: (filename, subcircuit_dir, init_state, measurement_basis_file)
                                # print(item)
                                # print(item[0][1])
                                if up == item[0][1]:
                                    pA.append(item[1])
                    for down in init:
                        for items in subcir_result:
                            for item in items:
                                # print(item)
                                # print(item[0][0])
                                if down == item[0][0]:
                                    pB.append(item[1])
                    subcirc_results = [pA, pB]
                    num_qubits = len(next(iter(pA[0]))) + len(next(iter(pB[0]))) - 1
                    reconstructed_dict = reconstruct_cutqc_normal(subcirc_results, num_qubits)
                    result = sorted(reconstructed_dict.items(), key=lambda x: x[1], reverse=True)
                    with open(reconstruct_result_path, 'w') as f:
                        json.dump(dict(result[:100]), f, indent=2)
                        f.close()
                    # cuts = cuts_list[idx]
                    # cut_order = cut_order_list[idx]
                    # cut_position = cut_position_list[idx]
                    # result = reconstruct_cutqc_full(subcirc_results=subcir_result, cuts=cuts,cut_order=cut_order, cuts_position=cut_position)
                    # with open(reconstruct_result_path, 'w') as f:
                    #     f.write(str(result))
                        
                # delete_files(circuit_path)
                
                # python本地重构结束
                
                # C++本地多进程重构
                
                # print(os.system('pwd'))
                # cpp_file_path = "./cut_and_reconstruct/five_tupo_renyi.cpp"

                # if not os.path.exists(cpp_file_path):
                #    print(f"文件 {cpp_file_path} 不存在于当前工作目录。")
                #    return
                
                # # 设置环境变量以允许以 root 用户运行 mpirun
                # os.environ['OMPI_ALLOW_RUN_AS_ROOT'] = '1'
                # os.environ['OMPI_ALLOW_RUN_AS_ROOT_CONFIRM'] = '1'

                # 编译 C++ 程序
                #compile_command = f"mpicxx -fopenmp -o ./cut_and_reconstruct/five_tupo_renyi -std=c++17 {cpp_file_path}"
                #os.system(compile_command)
                # 打印 currentPath 和 parallel_result_path 的值
                #print(f"输入路径 (currentPath): {currentPath}")
                #print(f"输出路径 (parallel_result_path): {parallel_result_path}")# 打印 currentPath 和 parallel_result_path 的值


                # 运行 C++ 程序
                #run_command = f"mpirun -np 5 ./cut_and_reconstruct/five_tupo_renyi --input {result_subcir_path} --output {reconstruct_result_path}"
                #os.system(run_command)

                # print(f"线路重构结果为：{result}")
                # file_path = f'{parallel_result_path}/reconstruct_result/circuit{idx}/result_rec.txt'
                # 检查路径是否存在，如果不存在则创建
                # os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # 将字典写入文件
                # with open(file_path, 'w', encoding='utf-8') as file:
                #    json.dump(result, file, ensure_ascii=False, indent=4)
                #print(f"字典已成功写入文件：{file_path}")
                # C++本地多进程重构结束
                
                
                # C++本地串行重构方法(取极大极小)
                elif cut_method == "manual":
                    chuan_cpp_file_path = "./cut_and_reconstruct/new_fangfa.cpp"
                    if not os.path.exists(chuan_cpp_file_path):
                        print(f"文件 {chuan_cpp_file_path} 不存在于当前工作目录。")
                        return
                    
                    # step1.编译
                    # compile_command = "g++ -o new_fangfa -std=c++17 {}".format(chuan_cpp_file_path)
                    # os.system(compile_command)

                    # step2.运行
                    run_command = f" ./new_fangfa --input {result_subcir_path} --output {reconstruct_result_path}"
                    # print(run_command)
                    os.system(run_command)
                    
                    import sys
                    sys.path.append("..")
                    from utils.post_process import cut_local_postprocess
                    cut_local_postprocess(f'{parallel_result_path}/local_reconstruct_result/')
                    # C++本地串行重构方法结束

            else:
                #非全连接线路
                # 检查 reconstruct_parallel.cpp 文件是否存在
                cpp_file_path = "./cut_and_reconstruct/reconstruct_parallel.cpp"
                if not os.path.exists(cpp_file_path):
                    print(f"文件 {cpp_file_path} 不存在于当前工作目录。")
                    return

                # 编译 C++ 程序
                compile_command = "mpicxx -o ./cut_and_reconstruct/reconstruct_parallel -std=c++17 {}".format(cpp_file_path)
                os.system(compile_command)

                # 运行 C++ 程序
                run_command = f"mpirun -np 2 ./cut_and_reconstruct/reconstruct_parallel {currentPath} {parallel_result_path}"
                os.system(run_command)


def reconstruct_cutqc_chuan(currentPath, seq_result_path):
    """
     编译并运行 rec.cpp 程序，并传递 currentPath 和 base_path 作为参数。

    参数:
     currentPath (str): 当前路径参数。
     base_path (str): 串行结果保存路径参数。
     """
    # 检查 rec.cpp 文件是否存在
    chuan_cpp_file_path = "/home/qcc/software-testing/reconstruct/rec.cpp"
    if not os.path.exists(chuan_cpp_file_path):
        print(f"文件 {chuan_cpp_file_path} 不存在于当前工作目录。")
        return
    # 编译 C++ 程序
    compile_command = "g++ -o rec -std=c++17 {}".format(chuan_cpp_file_path)
    os.system(compile_command)

    # 运行 C++ 程序
    run_command = f" ./rec {currentPath} {seq_result_path}"
    os.system(run_command)


def test_true(seq_result_path, parallel_result_path):
    """
   编译并运行 test_true.cpp 程序，并传递 seq_result_Path 和 parallel_result_path 作为参数。

   参数:
    seq_result_Path(str): 串行结果路径参数。
    parallel_result_path (str): 并行结果路径参数。
    """
    # 检查 test_true.cpp 文件是否存在
    cpp_file_path = "/home/qcc/software-testing/reconstruct/test_true.cpp"
    if not os.path.exists(cpp_file_path):
        print(f"文件 {cpp_file_path} 不存在于当前工作目录。")
        return
    # 编译 C++ 程序
    compile_command = "g++ -o test_true -std=c++17 {}".format(cpp_file_path)
    os.system(compile_command)

    # 运行 C++ 程序
    run_command = f" ./test_true {seq_result_path} {parallel_result_path}"
    os.system(run_command)

def quasi_to_real(quasiprobability):
    """
    将准概率分布转化为实际分布

    参数:
    quasiprobability (dict): 准概率分布的字典

    返回:
    dict: 归一化后的实际概率分布
    """
    # 过滤掉值为负的键值对
    filtered_dict = {k: v for k, v in quasiprobability.items() if v >= 0}

    # 计算剩余值的总和
    total_sum = sum(filtered_dict.values())

    # 对剩余键值对的值进行归一化
    normalized_dict = {k: v / total_sum for k, v in filtered_dict.items()}

    return normalized_dict


def reconstruct_cutqc_normal(subcirc_results, num_qubits):
    """
    使用精确方法重构电路的概率分布。

    参数:
    subcirc_results (list): 子电路的测量结果
    num_qubits (int): 量子位数

    返回:
    dict: 重构的概率分布
    """
    init = ['0', '1', '+', 'i']
    mes = ['I','Z', 'X', 'Y']

    p_rec = {}
    pA = subcirc_results[0]
    pB = subcirc_results[1]
    num_qubit_pB = len(next(iter(pB[0])))
    for i in range(0, 2 ** num_qubits):
        string = bin(i)[2:].zfill(num_qubits)
        substring1 = string[num_qubit_pB:]
        substring2 = string[:num_qubit_pB]
        substring11 = '0' + substring1
        substring12 = '1' + substring1
        p11 = pA[0].get(substring11, 0) * 2   # pA[0]  cir_0_sub0_none_I
        p12 = pA[1].get(substring12, 0) * 2   # pA[1]  cir_0_sub0_none_Z
        p13 = pA[2].get(substring11, 0) - pA[2].get(substring12, 0) # pA[2]  cir_0_sub0_none_X
        p14 = pA[3].get(substring11, 0) - pA[3].get(substring12, 0) # pA[3]  cir_0_sub0_none_Y
        p21 = pB[0].get(substring2, 0)   # pB[0]  cir_0_sub1_0_none
        p22 = pB[1].get(substring2, 0)   # pB[1]  cir_0_sub1_1_none
        p23 = 2 * pB[2].get(substring2, 0) - p21 - p22 # pB[2]  cir_0_sub1_+_none
        p24 = 2 * pB[3].get(substring2, 0) - p21 - p22 # pB[3]  cir_0_sub1_i_none
        p = (p11 * p21 + p12 * p22 + p13 * p23 + p14 * p24) / 2
        p_rec[string] = p
    # print(p_rec)
    real_dict = quasi_to_real(p_rec)
    return real_dict

if __name__ == "__main__":
    # 示例调用1 :10比特 2条子线路
    currentPath = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example"
    parallel_result_path = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_parallel"
    seq_result_path = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_chuan"
    reconstruct_cutqc(currentPath, parallel_result_path)
    reconstruct_cutqc_chuan(currentPath, seq_result_path)
    test_true(seq_result_path, parallel_result_path)

    # 示例调用2 :15比特 3条子线路
    # currentPath = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example"
    # parallel_result_path = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_parallel"
    # seq_result_path="/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_chuan"
    # reconstruct_cutqc(currentPath, parallel_result_path)
    # reconstruct_cutqc_chuan(currentPath, seq_result_path)
    # test_true(seq_result_path, parallel_result_path)

    # 示例调用3 :20比特 4条子线路
    # currentPath = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example"
    # parallel_result_path = "/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_parallel"
    # seq_result_path="/home/qcc/software-testing/reconstruct/chuan_yanzheng_example/reconstruct_results_chuan"
    # reconstruct_cutqc(currentPath, parallel_result_path)
    # reconstruct_cutqc_chuan(currentPath, seq_result_path)
    # test_true(seq_result_path, parallel_result_path)
