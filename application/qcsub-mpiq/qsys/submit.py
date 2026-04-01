import shutil, requests, json, os
# import pymysql
import time, string, random, ast

import sys
sys.path.append("..")
from utils.times import timer_decorator_env
                    
def hex_to_bin(origin_result, measure_count):
    result = [
    	{bin(int(k.replace('0x', ''), 16))[2:].zfill(measure_count): v for k, v in d.items()}
    	for d in origin_result
		]
    return result[0]

# 读取 OpenQASM 文件并统计 measure 操作次数
def count_measure_operations(content):
    # 按行分割并统计
    lines = content.split('\n')
    measure_count = 0

    for line in lines:
        if line.strip().startswith("measure"):  # 忽略空格并检查行首
            measure_count += 1
    return measure_count

def generate_string(length=10):
    letters_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_digits) for _ in range(length))

def gen_target_id():
    timestamp = time.time()
    # 将时间戳转换为本地时间
    local_time = time.localtime(timestamp)
    # 格式化为字符串（精确到秒）
    date_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    # 获取当前时间戳（纳秒级）
    timestamp_ns = time.time_ns()
    # 将纳秒部分提取出来
    nanoseconds = timestamp_ns % 1_000_000_000
    # 格式化为字符串（精确到纳秒）
    date_str_ns = f"{date_str}.{nanoseconds:09d}"
    return date_str_ns

def submit(qasm,os_ip,method,chip):
    #任务id
    # task_id = generate_string(32)    #'fc0de40b1e0411eeb823204747dbca29' 
    task_id = gen_target_id()
    # print(task_id)
    #任务名
    task_nam = generate_string(14) #' 20230717test17'

    ## 任务创建服务后台
    myUrl = 'http://'+os_ip+':8288/task/quantum/create'
    headers = {
        'Host': os_ip +':8288',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'Content-Length': '384',
        'Origin': 'http://'+os_ip+':8289',
        'Connection': 'keep-alive',
        'Referer': 'http://'+os_ip+':8289/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }
    chipid=0
    if chip=='Chaoyue':
        chipid=1
    date_list = {
        'id': task_id,
        'user_id': '', # 接受任何类型的返回数据
        'name': task_nam, # 发送数据为json
        'qinit': '2',   #要跟ir相匹配
        'graph': '',
        'ir': qasm,
        'backend_id': chipid,
        'machine_id': method
    }

    try:
        print('================开始上传线路至操作系统====================')
        ret = requests.post(url=myUrl, headers=headers, data=json.dumps(date_list))
        #ret = requests.post(url=myUrl, headers=headers, json=data,timeout = cfg.timeout )
        response_data = ret.json()
        print(f"response_data {response_data}")
    except Exception as e:
        print('getCapacityData [Error]: ' + str(e))
    # print('=====================上传结果=====================')
    # print(response_data)
    ## 任务提交服务后台
    myUrl = 'http://'+os_ip+':8288/task/quantum/submit'
    headers = {
        'Host': os_ip+':8288',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'Content-Length': '384',
        'Origin': 'http://'+os_ip+':8289',
        'Connection': 'keep-alive',
        'Referer': 'http://'+os_ip+':8289/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    } #包头

    date_list = {
        'id': task_id,
        'user_id': '' # 接受任何类型的返回数据
    }

    try:
        print('================待运行线路提交至qcc进行====================')
        ret = requests.post(url=myUrl, headers=headers, data=json.dumps(date_list))
        #ret = requests.post(url=myUrl, headers=headers, json=data,timeout = cfg.timeout )
    #     response_data = ret.json()
    except Exception as e:
        print('getCapacityData [Error]: ' + str(e))
    print('===================线路提交结果====================')
    print(response_data)
    print('================qcc后台进行编译====================')
    return task_id

def get_res(task_id,os_ip):
    try:
        db = pymysql.connect(host=os_ip,user="root",password='ZDY123456789!',database='django_mysql')
        # print("数据库连接成功")
    except pymysql.Error as e:
        print("数据库连接失败："+str(e))

    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()

    sql_query_all = "select status,result,id from db_quantum_task where id = %s"
    # 表示从左到右每个占位符所表示的元素的内容
    value = task_id
    cursor.execute(sql_query_all, value)
    result = cursor.fetchall()
    print(result)
    if len(result)>0:
        if result[0][0]== 4:
            print('===================运行完成，结果如下==================')
            print(result[0][1])
            flag = False
        db.close()
    else:
        flag = True 
        db.close()
    return result[0][1]

def submit_list(cir_list, os_ip, method, chip):
    taskid_list=[]
    for cir in cir_list:
        taskid_list.append(submit(cir, os_ip, method, chip))
    return taskid_list

def get_res_list(taskid_list,os_ip):
    res_list={}
    for taskid in taskid_list:
        temp = get_res(taskid,os_ip)
        # print(f"task id is {taskid}\n  result is {temp}")
        res_list[taskid]=temp
    return res_list

def get_res_list_origin(qm, taskid_list, qubit_num_list):
    TIME_OUT = 10
    res_list = {}
    for i in range(len(taskid_list)):
        taskid = taskid_list[i]
        print(f"Now the task_id is {taskid}")
        qubit_num = qubit_num_list[i]
        while True:
            query_result = qm.query_task_state(taskid)
            if query_result['taskState'] == '3':#状态为3指任务运行成功
                #print(query_result)
                async_result = qm.parse_probability_result(query_result['taskResult'])# 解析概率信息
                async_count = qm.parse_prob_counts_result(query_result['probCount'])# 解析概率信息
                if len(async_result)<1:
                    time.sleep(1)  # 延时2秒
                    continue
                else:
                    #print(f"----task state----\n{query_result['taskState']}")
                    print("quantum task has been done, the result will return soon...")
                    result = hex_to_bin(async_count, qubit_num)
                    #result = async_count
                    res_list[taskid] = str(result)
                    break
                
            elif query_result['taskState'] == '4' or query_result['taskState'] == '35': #状态为4指任务失败，35指任务取消（指用户在页面上手动取消）
                print(f"state: {query_result['taskState']}")
                print(f"errCode: {query_result['errCode']}")
                print(f"errInfo: {query_result['errInfo']}")
                res_list[taskid] = {query_result['errInfo']}
                #print(f"Task measure failed Please measure later, errInfo:{query_result[1]}")
                break
            
            else:
                #print(f"state: {query_result['taskState']}")
                print("please wait for a moment, the task is running...")
                time.sleep(0.5) #延时0.5秒
                continue
        #print("####",res_list)
    return res_list
    
def check_list(lst):
    for k,v in lst.items():
        if not v:  # 检查字符串是否为空
            return False
    return True

def run_circuits(cir_list, os_ip, method, chip, shots):
    # print(cir_list)
    # print(os_ip)
    # print(method)
    
    if chip=='Wukong':
        from pyqpanda import QPilotOSMachine, convert_qasm_string_to_originir
        from pyqpanda3.intermediate_compiler import convert_qasm_string_to_qprog, convert_qprog_to_qasm
        from pyqpanda3.intermediate_compiler import convert_qprog_to_originir

        qm = QPilotOSMachine('Pilot')
        qm.set_config(72, 72)
        qm.init(os_ip, True, '63DF5465FE0A42F498E1654A5F92D636')  # 70938AE993794E189E116569222F52E2
        taskid_list = []
        qubit_num_list = []
        
        for cir in cir_list:
            # qprog = convert_qasm_string_to_qprog(qasm_str = cir)
            # qir = convert_qprog_to_originir(qprog)
            qir =  convert_qasm_string_to_originir(qasm_str=cir)
            print("#"*20)
            print(qir)
            print("#"*20)
            
            # 离子阱：IonTrap (6qubits,shots 10-1000)      光量子：PQPUMESH8（3qubits），   超导102比特：WK_C102_400/WK_C102-2,  超导72比特：72
            taskid = qm.async_real_chip_measure(prog=qir,     # WK_C102_400   72
                    shot=shots, chip_id='WK_C102-2', is_mapping=True, is_amend=True, point_label=1)    # is_mapping=True, is_amend=True,
                                                
            taskid_list.append(taskid)  
            qubit_num_list.append(count_measure_operations(cir))     
        print(f"taskid_list: {taskid_list}")
        #循环查询任务状态
        flag=True
        while(flag):
            time.sleep(0.5)
            res_dict = get_res_list_origin(qm, taskid_list, qubit_num_list)
            if check_list(res_dict):
                flag=False
                res_list = []
                for taskid in taskid_list:
                    res_dict[taskid] =  dict(sorted(ast.literal_eval(res_dict[taskid]).items(), key=lambda item: item[1], reverse=True))
                    res_list.append(res_dict[taskid])
                # print('===================完成运行==================')
                # print(taskid_list)
                # print(res_list)
                print(res_list)
                return res_list   
              
    elif chip=='Simulator':
        from qiskit import Aer,execute,QuantumCircuit
        res_list = []
        for cir in cir_list:        
            backend = Aer.get_backend('qasm_simulator')
            qc = QuantumCircuit.from_qasm_str(cir)
            job = execute(qc, backend, shots=shots)
            result = job.result()
            counts = result.get_counts(qc)
            res_list.append(str(counts))
        return res_list
    
    elif chip in ["tianyan176-2","tianyan176","tianyan-287","tianyan504"]:
        from qclib.execute import submit_circuit
        res_list = []
        for cir in cir_list:
            # print(cir)
            result = submit_circuit(cir, chip, shots)
            res_list.append(result)
        return res_list
    
    # 其他芯片如chaoyue
    else:  
        res_list = []
        taskid_list = submit_list(cir_list, os_ip, method, chip)
        flag=True
        while(flag):
            time.sleep(0.5)
            res_dict=get_res_list(taskid_list, os_ip)
            if check_list(res_dict):
                flag=False
                res_list = []
                for taskid in taskid_list:
                    res_list.append(res_dict[taskid])
                # print('===================完成运行==================')
                # print(taskid_list)
                # print(res_list)
                return res_list
                
            # print('===================等待结果==================')


# 将字符串形式的字典转换为真正的字典
def convert_to_dict(dict_str):
    # 替换单引号为双引号，以满足json.loads的要求
    dict_str = dict_str.replace("'", '"')
    return json.loads(dict_str)

def em_fun(subcir_results_folder, res):
#     subcir_results_folder='/home/qcc/software-testing/20250118/qsys/Qsys/circuit_0/subcircuit_1'
    # for idx,qasm_list in enumerate(qasm_lists):
    #     file_name = f"subcir_{idx}_result.txt"
    #     subcir_result_file = os.path.join(subcir_results_folder, file_name)
    #     print('================5=============================')
    #     print(qasm_list)

                # 获取列数（假设每个子数组的长度相同）
    num_columns = len(res[0])

    # 遍历每一列，将内容写入文件
    for col in range(num_columns):
        file_name = f"subcir_{col}_result.txt"
        subcir_result_file = os.path.join(subcir_results_folder, file_name)
        # print('666666666666666666666666666666')
        # print(subcir_result_file)
        if not os.path.exists(subcir_results_folder):
            os.makedirs(subcir_results_folder)

        # with open(subcir_result_file, "w") as file:
        #     pass  # 创建一个空文件
        with open(subcir_result_file, "w") as file:
            for row in res:
                if col < len(row):  # 确保索引不会超出范围
                    dictionary = convert_to_dict(row[col])
                    for key, value in dictionary.items():
                        file.write(f"{key}: {value}\n")
                    file.write("****\n")  # 在不同字典之间添加分隔符
        # print(f"run circuits result save path :{subcir_result_file}")

        # my_dict0 = ast.literal_eval(qasm_list[0])
        # my_dict1 = ast.literal_eval(qasm_list[1])
        # my_dict2 = ast.literal_eval(qasm_list[2])
        # os.makedirs(subcir_results_folder, exist_ok=True)
        # save_dict_to_txt(subcir_result_file, my_dict0)
        # save_split(subcir_result_file)
        # save_dict_to_txt_a(subcir_result_file, my_dict1)
        # save_split(subcir_result_file)
        # save_dict_to_txt_a(subcir_result_file, my_dict2)
    

def save_dict_to_txt(file_path, dictionary):
    """
    将字典保存到txt文件中
    :param file_path: txt文件的路径
    :param dictionary: 要保存的字典
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for key, value in dictionary.items():
                f.write(f"{key}:{value}\n")
        # print(f"线路结果已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存字典时出错：{e}")
        
def save_dict_to_txt_a(file_path, dictionary):
    """
    将字典保存到txt文件中
    :param file_path: txt文件的路径
    :param dictionary: 要保存的字典
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            for key, value in dictionary.items():
                f.write(f"{key}:{value}\n")
        # print(f"线路结果已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存字典时出错：{e}")
        
def save_split(file_path):
    """
    将字典保存到txt文件中
    :param file_path: txt文件的路径
    :param dictionary: 要保存的字典
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"****\n")
        print(f"线路结果已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存字典时出错：{e}")

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
    #     print(f"目录 {directory} 及其内容已删除")
    # else:
    #     print(f"目录 {directory} 不存在")

@timer_decorator_env()
def process_list(qasm_lists, compiled_qasms_path_file, os_ip, cut, method, em, chip, parallel_output_file, shots, subcircuit_1_exec_times=1):
    current_folder = os.path.join(parallel_output_file, 'result_cir')
    delete_files(current_folder)
    
    res_file_list = current_folder  # 返回结果的根目录

    for circuit_idx, qasm_cirs in enumerate(qasm_lists):
        # 创建主电路结果目录
        result_folder = os.path.join(current_folder, f"circuit_{circuit_idx}")
        
        if cut:        
            for subidx, qasm_list in enumerate(qasm_cirs):
                # 获取当前子电路对应的所有 QASM 文件路径
                subcircuit_qasm_paths = compiled_qasms_path_file[circuit_idx][subidx]
                # 创建子电路结果目录
                subcir_results_folder = os.path.join(result_folder, f"subcircuit_{subidx}")
                os.makedirs(subcir_results_folder, exist_ok=True)
                
                # 确定执行次数，subcircuit_1 执行subcircuit_1_exec_times次，其他执行1次
                exec_times = subcircuit_1_exec_times if subidx == 1 else 1
                
                for i in range(exec_times):
                    res_list = run_circuits(qasm_list, os_ip, method, chip, shots)
                    print(f"Run success! (Execution {i+1}/{exec_times}) And the returned results are:\n", res_list)
                    # 遍历每个结果和对应的 QASM 文件路径
                    for idx, (result_dict, qasm_path) in enumerate(zip(res_list, subcircuit_qasm_paths)):
                        # 提取 QASM 文件名并生成结果文件名
                        qasm_filename = os.path.basename(qasm_path)
                        # 第一次执行不带后缀，后续执行带后缀
                        result_filename = f"{os.path.splitext(qasm_filename)[0]}_result{'_'+str(i+1) if i > 0 else ''}.txt"
                        result_file = os.path.join(subcir_results_folder, result_filename)
                        
                        # 确保字典格式正确并保存
                        my_dict = ast.literal_eval(result_dict) if isinstance(result_dict, str) else result_dict
                        save_dict_to_txt(result_file, my_dict)
        else:
            for subidx, qasm_list in enumerate(qasm_cirs):
                # 获取当前子电路对应的所有 QASM 文件路径
                subcircuit_qasm_paths = compiled_qasms_path_file[circuit_idx][subidx]
                # 创建子电路结果目录
                subcir_results_folder = os.path.join(result_folder, f"subcircuit_{subidx}")
                os.makedirs(subcir_results_folder, exist_ok=True)

                res_list = run_circuits(qasm_list, os_ip, method, chip, shots)
                print("Run success! And the returned results are:\n", res_list)
                for idx, (result_dict, qasm_path) in enumerate(zip(res_list, subcircuit_qasm_paths)):
                    # 提取 QASM 文件名并生成结果文件名
                    qasm_filename = os.path.basename(qasm_path)
                    result_filename = f"{os.path.splitext(qasm_filename)[0]}_result.txt"
                    result_file = os.path.join(subcir_results_folder, result_filename)
                    # 确保字典格式正确并保存
                    my_dict = ast.literal_eval(result_dict) if isinstance(result_dict, str) else result_dict
                    save_dict_to_txt(result_file, my_dict)       
    if not em and not cut:              
        from utils.post_process import qsys_postprocess
        qsys_postprocess(current_folder)
    
    return res_file_list

# 辅助函数：保存字典到文本
def save_dict_to_txt(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

