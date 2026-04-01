import sys, os
import argparse
import json
import logging
from dotenv import load_dotenv
from utils.times import timer_decorator_env

class QCSUBPost():
    def __init__(self):
        """
            初始化QCSUBPost类的配置参数。
            
            该类用于读取子线路执行的结果，完成结果重构，输出最终的结果。
            
            参数说明：
                sub_circuit_res_path (str): 子线路结果存储路径
                parallel_output_file (str): 并行执行结果输出目录，默认为 './result/'
                local_log_path (str): 本地日志存储路径，默认为 './logs-2/'
                error_mitigation (bool): 是否启用误差缓解功能
                cut_circuit (bool): 是否启用线路切割功能
                cuts_list (list): 存储线路切割信息的列表
                cut_position_list (list): 存储切割位置信息的列表
                cut_order_list (list): 存储切割顺序信息的列表
                cut_method (str): 线路切割方式，可选 'automatic'（自动）或 'manual'（手动）
                supercomputing (bool): 是否使用超算资源
                super_nodes (int): 超算节点数量
                dcu (bool): 是否使用DCU计算资源
        """
        self.sub_circuit_res_path = None
        self.parallel_output_file = './result/'
        self.local_log_path = './logs-2/'
        self.error_mitigation = False
        self.cut_circuit = False
        self.cuts_list = []
        self.cut_position_list = []
        self.cut_order_list = []
        self.cut_method = 'automatic'
        self.supercomputing = False
        self.super_nodes = 32                                # 超算节点数量
        self.dcu = False                                     # 是否使用DCU

    def find_result_path(self):
        """
        自动查找子线路结果路径
        扫描 ./result/result_cir/ 目录
        """
        result_cir_path = os.path.join(self.parallel_output_file, 'result_cir')
        if os.path.exists(result_cir_path):
            return result_cir_path
        return None

    def get_script_dir(self):
        """获取脚本所在目录的绝对路径"""
        return os.path.dirname(os.path.abspath(__file__))

    @timer_decorator_env()
    def run(self): 
        # 如果没有指定子线路结果路径，自动查找
        if self.sub_circuit_res_path is None:
            self.sub_circuit_res_path = self.find_result_path()
            if self.sub_circuit_res_path is None:
                print(f"错误: 未找到子线路结果路径，请使用 -r 参数指定")
                exit(1)
            print(f"自动找到子线路结果路径: {self.sub_circuit_res_path}")
        
        # 检查结果路径是否存在
        if not os.path.exists(self.sub_circuit_res_path):
            print(f"错误: 子线路结果路径不存在: {self.sub_circuit_res_path}")
            exit(1)
        
        # 读取切割信息
        cut_info_path = os.path.join(self.parallel_output_file, 'cut_info.json')
        if self.cut_circuit and os.path.exists(cut_info_path):
            with open(cut_info_path, 'r') as f:
                cut_info = json.load(f)
            self.cuts_list = cut_info.get('cuts_list', [])
            self.cut_position_list = cut_info.get('cut_position_list', [])
            self.cut_order_list = cut_info.get('cut_order_list', [])
            self.cut_method = cut_info.get('cut_method', 'automatic')
            print(f"已读取切割信息: {cut_info_path}")
        elif self.cut_circuit:
            print(f"警告: 未找到切割信息文件: {cut_info_path}")
        
        # 误差缓解模块
        if self.error_mitigation:
            from mitigation.mitigation import mitigate_function
            self.mited_res_path, _, _ = mitigate_function(
                self.sub_circuit_res_path, 
                self.parallel_output_file, 
                None  # compiled_qasms_path_folder，可能不需要
            )
            print(f"误差缓解结果存放路径: {self.mited_res_path}")
        
        # 重构模块
        if self.cut_circuit:
            if self.error_mitigation:
                self.reconstruct_inout_result_dir = self.mited_res_path
            else:
                self.reconstruct_inout_result_dir = self.sub_circuit_res_path
            
            from cut_and_reconstruct.reconstruct_helpler import reconstruct_cutqc
            reconstruct_cutqc(
                self.reconstruct_inout_result_dir, 
                self.parallel_output_file, 
                self.local_log_path,
                self.cuts_list, 
                self.cut_order_list, 
                self.cut_position_list, 
                self.cut_method,
                self.supercomputing, 
                self.super_nodes, 
                self.dcu
            )
            print("重构完成")
        else:
            print("未启用线路切割，无需重构")

    def parseArgs(self):
        '''
        常规参数：
            1.子线路结果路径
            2.输出文件名
        可选参数：
            1.误差缓解功能
            2.超算资源使用
        '''
        parser = argparse.ArgumentParser(description="QCSUBPost usage help document")
        parser.add_argument("-r", "--sub_circuit_res_path", type=str, help="specify the sub circuit result path, if not provided, will auto-find")
        parser.add_argument("-o", "--output_file", default=self.parallel_output_file, type=str, help="specify the output file")
        parser.add_argument("-em", "--error_mitigation", action='store_true', default=False, help="specify whether to use quantum error mitigation, default FALSE.")
        parser.add_argument("-cut", "--cut_circuit", action='store_true', default=False, help="specify whether the circuits are cut, default FALSE.")
        parser.add_argument("-super", "--supercomputing", action='store_true', default=False, help="specify whether to use supercomputing for construction, default FALSE.")
        parser.add_argument("-super_nodes", "--super_nodes", type=int, default=32, help="the number of super computing nodes for reconstruction, default use 32.")
        parser.add_argument("-dcu", "--use_dcu", action='store_true', default=False, help="specify whether to use supercomputing with dcu for construction, default FALSE.")
        parser.add_argument("-local_log_path", "--local_log_path", default=self.local_log_path, type=str, help="specify the path for storing log file")

        args = parser.parse_args()

        if args.sub_circuit_res_path:
            self.sub_circuit_res_path = args.sub_circuit_res_path
        # 注意：这里不再强制要求输入结果路径，会在run()中自动查找
            
        if args.output_file:
            self.parallel_output_file = args.output_file

        if args.local_log_path:
            self.local_log_path = args.local_log_path
            
        if args.error_mitigation:
            self.error_mitigation = True

        if args.cut_circuit:
            self.cut_circuit = True

        if args.supercomputing:
            self.supercomputing = True

        if args.supercomputing and args.super_nodes:
            self.super_nodes = args.super_nodes
        elif not args.supercomputing and args.super_nodes:
            self.super_nodes = 0
        
        if args.use_dcu:
            self.dcu = True

        show_config_str = f"""
=======================================================================
                        QCSUBPost configation
=======================================================================
{'the sub circuit result path':>50}:  {self.sub_circuit_res_path if self.sub_circuit_res_path else 'Auto-find'}
{'if use quantum error mitigation':>50}:  {self.error_mitigation}
{'if use quantum circuit reconstruction':>50}:  {self.cut_circuit}
{'if use supercomputing for reconstruction':>50}:  {self.supercomputing}
{'the number of superNodes for reconstruction':>50}:  {self.super_nodes}
{'the output file is':>50}:  {self.parallel_output_file}
{'the path of log file is':>50}:  {self.local_log_path}

=======================================================================
"""

        print(show_config_str)

@timer_decorator_env()
def main():
    # load .env中的变量
    load_dotenv()
    qcsub_post = QCSUBPost()
    qcsub_post.parseArgs()
    qcsub_post.run()

if __name__ == "__main__":
    main()