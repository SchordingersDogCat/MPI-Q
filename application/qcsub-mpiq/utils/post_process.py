import json
import os

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
                    numeric_value = float(value)
                except ValueError:
                    try:
                        numeric_value = float(value)
                    except ValueError:
                        print(f"警告：文件 '{txt_path}' 内容不是有效的数字")
                
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

output_file = r"./result/qcsub_result/qcsub_result.txt"

def cut_postprocess(root_dir):
    # 使用该后处理函数存在两个使用场景
    # 1.切割+操作系统任务调度+重构  QCSUB -i test.qasm -cut 
    # 2.切割+操作系统任务调度+误差缓解+重构 QCSUB -i test.qasm -cut -em
    
    # 遍历root_dir目录及其子目录
    result_dict = {}
    for subdir, dirs, files in os.walk(root_dir):
        # 获取当前子目录相对于root_dir的相对路径，作为字典的key
        relative_path = os.path.relpath(subdir, root_dir)
        if relative_path == '.':
            dir_name = os.path.basename(root_dir)
        else:
            dir_name = relative_path.replace(os.sep, '_')  # 使用下划线替换路径分隔符
        
        # 查找并处理result_rec.txt文件
        if 'result_rec.txt' in files:
            file_path = os.path.join(subdir, 'result_rec.txt')
            with open(file_path, 'r', encoding='utf-8') as file:
                content = json.loads(file.read())
                result_dict[dir_name] = content
    
    # 将结果保存为JSON文件
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
    print(f"当前提交任务运行结果已成功写入文件：{output_file}")

def cut_local_postprocess(root_dir):
    # 使用该后处理函数存在两个使用场景
    # 1.切割+操作系统任务调度+重构  QCSUB -i test.qasm -cut 
    # 2.切割+操作系统任务调度+误差缓解+重构 QCSUB -i test.qasm -cut -em
    
    # 遍历root_dir目录及其子目录
    result_dict = {}
    for subdir in os.listdir(root_dir):
        subsub_dir = os.path.join(root_dir,subdir)
        for file in os.listdir(subsub_dir):
            file_path = os.path.join(subsub_dir, file)
            content = txt_to_dict(file_path)
            result_dict[subdir] = content

    # 将结果保存为JSON文件
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
    print(f"[postprocess] 当前提交任务运行结果已成功写入文件：{output_file}")

def qsys_postprocess(root_dir):
    # 当操作系统的任务调度结束即返回结果时使用该后处理函数，使用场景为
    # 1.操作系统任务调度 QCSUB -i test.qasm
    # 遍历root_dir目录及其子目录
    result_dict = {}
    file_path_list = os.listdir(f"{root_dir}")
    file_path_list = sorted(file_path_list, key=sort_key)
    for l1_entry in file_path_list:
        l1_path = os.path.join(root_dir, l1_entry)
        if os.path.isdir(l1_path):
            for l2_entry in os.listdir(l1_path):
                l2_path = os.path.join(root_dir, l1_entry, l2_entry)
                if os.path.isdir(l2_path):
                    for l3_entry in os.listdir(l2_path):
                        if l3_entry.endswith(".txt"):
                            full_path = os.path.join(root_dir, l1_entry, l2_entry, l3_entry)
                            with open(full_path, 'r', encoding='utf-8') as file:                            
                                content = json.loads(file.read())
                            result_dict[l1_entry] = content
    # 将结果保存为JSON文件
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
    print(f"当前提交任务运行结果已成功写入文件：{output_file}")
    
def mitigation_postprocess():
    # 当误差缓解模块结束即返回结果时使用该后处理函数，使用场景为
    # 1.操作系统任务调度+误差缓解 QCSUB -i test.qasm -em
    pass

if __name__ == '__main__':
    file_path = '../result/local_reconstruct_result/'
    for subdir in os.listdir(file_path):
        print(subdir)
    # cut_postprocess(file_path)
    # with open(output_file, 'r', encoding='utf-8') as file:
    #     file_content = file.read()
    # #print(f"文件内容: {file_content}")  # 调试信息，打印文件内容
    # if not file_content.strip():
    #     print("文件内容为空")
    # # 解析 JSON 数据
    # json_data = json.loads(file_content)
    # print(json.dumps(json_data, indent=4))