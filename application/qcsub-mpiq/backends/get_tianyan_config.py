import requests
import json, re
from cqlib.utils import QcisToQasm, QasmToQcis
from cqlib import TianYanPlatform  
from cqlib.utils import LaboratoryUtils
from cqlib.utils import QCIS_Simplify
import numpy as np

def tianyan_topography(machine_name):
    topography_rename = {}
    if machine_name == "tianyan176-2" or machine_name == "tianyan176":
        k = 0
        for i in range(5):
            for j in range(6):
                if j<=4:
                    topography_rename[(12*i+j,12*i+j+6)] = "G"+str(k)
                    topography_rename[(12*i+j,12*i+j+7)] = "G"+str(k+1)
                    k+=2
                else:
                    topography_rename[(12*i+j,12*i+j+6)] = "G"+str(k)
                    k+=1
            for j in range(6):
                if j<=4:
                    topography_rename[(12*i+j+6,12*i+j+12)] = "G"+str(k)
                    topography_rename[(12*i+j+7,12*i+j+12)] = "G"+str(k+1)
                    k+=2
                else:
                    topography_rename[(12*i+j+6,12*i+j+12)] = "G"+str(k)
                    k+=1
        return topography_rename
    elif machine_name == "tianyan24":
        k = 0
        for i in range(1):
            for j in range(11):
                topography_rename[(12*i+j,12*i+j+1)] = "G"+str(k)
                topography_rename[(12*i+j,12*i+j+12)] = "G"+str(k+11)
                k+=1
            topography_rename[(12*i+11,12*i+11+12)] = "G"+str(k+11)
            k+=1
        k = k+11
        for i in range(1,2):
            for j in range(11):
                topography_rename[(12*i+j,12*i+j+1)] = "G"+str(k)
                k+=1       
        
    elif machine_name == "tianyan-287":
        topography_rename = {}
        k = 1
        for i in range(3):
            for j in range(1, 8):
                if j <= 6:
                    topography_rename[(28 * i + j, 28 * i + j + 7)] = "G" + str(k)
                    topography_rename[(28 * i + j, 28 * i + j + 8)] = "G" + str(k + 1)
                    k += 2
                else:
                    topography_rename[(28 * i + j, 28 * i + j + 7)] = "G" + str(k)
                    k += 1

            for j in range(1, 8):
                if j <= 6:
                    topography_rename[(28 * i + j + 7, 28 * i + j + 14)] = "G" + str(k)
                    topography_rename[(28 * i + j + 7, 28 * i + j + 15)] = "G" + str(k + 1)
                    k += 2
                else:
                    topography_rename[(28 * i + j + 7, 28 * i + j + 14)] = "G" + str(k)
                    k += 1

            for j in range(1, 8):
                if j <= 1:
                    topography_rename[(28 * i + j + 14, 28 * i + j + 21)] = "G" + str(k)
                    k += 1
                else:
                    topography_rename[(28 * i + j + 14, 28 * i + j + 20)] = "G" + str(k)
                    topography_rename[(28 * i + j + 14, 28 * i + j + 21)] = "G" + str(k + 1)
                    k += 2

            for j in range(1, 8):
                if j <= 1:
                    topography_rename[(28 * i + j + 21, 28 * i + j + 28)] = "G" + str(k)
                    k += 1
                else:
                    topography_rename[(28 * i + j + 21, 28 * i + j + 27)] = "G" + str(k)
                    topography_rename[(28 * i + j + 21, 28 * i + j + 28)] = "G" + str(k + 1)
                    k += 2

        for i in range(3, 4):
            for j in range(1, 8):
                if j <= 6:
                    topography_rename[(28 * i + j, 28 * i + j + 7)] = "G" + str(k)
                    topography_rename[(28 * i + j, 28 * i + j + 8)] = "G" + str(k + 1)
                    k += 2
                else:
                    topography_rename[(28 * i + j, 28 * i + j + 7)] = "G" + str(k)
                    k += 1

            for j in range(1, 8):
                if j <= 6:
                    topography_rename[(28 * i + j + 7, 28 * i + j + 14)] = "G" + str(k)
                    topography_rename[(28 * i + j + 7, 28 * i + j + 15)] = "G" + str(k + 1)
                    k += 2
                else:
                    topography_rename[(28 * i + j + 7, 28 * i + j + 14)] = "G" + str(k)
                    k += 1
    return topography_rename   


def tianyan_machine_config(login_key, backend: "tianyan176"):
    platform = TianYanPlatform(login_key=login_key, machine_name = backend)
    lu = LaboratoryUtils()
    config_save = platform.download_config()
    coupling_map =  lu.get_coupling_map(config_save)
    topography = [[item[1], item[0]] if item[0] > item[1] else [item[0], item[1]] for item in coupling_map]
    topography_rename = tianyan_topography(backend)
    props = {}
    #print(config_save['twoQubitGate']['czGate']['gate error']['update_time']) #校准时间
    CZ_error = config_save['twoQubitGate']['czGate']['gate error']['param_list'] #CZ错误率
    CZ_name = config_save['twoQubitGate']['czGate']['gate error']['qubit_used']  #相关的CZ门名称，与topography_rename相对应
    CZ_error_list = {}  # cz gate_error dict
    for key, value in topography_rename.items():
        if value in CZ_name:
            CZ_error_list[f"({key[0]},{key[1]})"] = CZ_error[CZ_name.index(value)]
            CZ_error_list[f"({key[1]},{key[0]})"] = CZ_error[CZ_name.index(value)]
        else:
            CZ_error_list[f"({key[0]},{key[1]})"] = np.nan
            CZ_error_list[f"({key[1]},{key[0]})"] = np.nan

    singleQubit_error_dict = {}
    singleQubit_readoutError_dict = {}
    qubit_frequency_dict = {}
    readout_frequency_dict = {}
    singleQubit_error = config_save['qubit']['singleQubit']['gate error']['param_list']
    singleQubit_list = config_save['qubit']['singleQubit']['gate error']['qubit_used']
    singleQubit_readoutErrorlist = config_save['readout']['readoutArray']['Readout Error']['param_list']
    qubit_frequency_list = config_save['qubit']['frequency']['f01']['param_list']
    
    # 正则表达式，匹配所有形式的数字
    pattern1 = r'\d+'
    for i in range(len(singleQubit_list)):
        number = int(re.findall(pattern1, singleQubit_list[i])[0])
        singleQubit_error_dict[number] = singleQubit_error[i]
        singleQubit_readoutError_dict[number] = singleQubit_readoutErrorlist[i]
        qubit_frequency_dict[number] = qubit_frequency_list[i]
        readout_frequency_dict[number] = None
    # singleQubit_error_dict 
    props['backend'] = backend
    props['singleQubit_error'] = singleQubit_error_dict 
    # singleQubit_readoutError_dict
    props['readoutError'] = singleQubit_readoutError_dict 
    props['CZ_error'] = CZ_error_list
    props['qubit_frequency'] = qubit_frequency_dict
    props['readout_frequency'] = readout_frequency_dict
    sub_list = []  # 无效边列表
    for edge in topography:
        if props['CZ_error'][f"({edge[0]},{edge[1]})"] is np.nan:
            sub_list.append([edge[0],edge[1]])

    topography = [x for x in topography if x not in sub_list]

    node_list = []
    for item in topography:
        node_list.append(item[0])
        node_list.append(item[1])
    from collections import Counter
    node_dict = dict(Counter(node_list))

    dissociate_list = [] #孤立边
    for edge in topography:
        if node_dict[edge[0]] < 2:
            if node_dict[edge[0]] == node_dict[edge[1]]:
                dissociate_list.append(edge)

    topography = [x for x in topography if x not in dissociate_list]

    graph_nodes = []
    for item in topography:
        graph_nodes.append(item[0])
        graph_nodes.append(item[1])

    graph_nodes = list(set(graph_nodes))
    
    bidirectional_topography = []
    for edge in topography:
        bidirectional_topography.append(edge)
        bidirectional_topography.append([edge[1],edge[0]])
    bidirectional_topography = sorted(bidirectional_topography)  

    props['topography'] = topography
    props['bidirectional_topography'] = bidirectional_topography
    props['singleQubit_update_time'] = config_save['qubit']['singleQubit']['gate error']['update_time'] #单比特门校准时间
    props['readout_update_time'] = config_save['readout']['readoutArray']['Readout Error']['update_time'] #读取错误率校准时间
    props['twoQubitGate_update_time'] = config_save['twoQubitGate']['czGate']['gate error']['update_time'] #双比特门校准时间  

    # t1、t2的单位为us
    props['t1_dict'] = {}
    index = 0
    for item in config_save['qubit']['relatime']['T1']['qubit_used']:
        number = int(re.findall(pattern1, item)[0])
        props['t1_dict'][number] = config_save['qubit']['relatime']['T1']['param_list'][index]
        index+=1

    props['t2_dict'] = {}
    index = 0
    for item in config_save['qubit']['relatime']['T2']['qubit_used']:
        number = int(re.findall(pattern1, item)[0])
        props['t2_dict'][number] = config_save['qubit']['relatime']['T2']['param_list'][index]
        index+=1
    
    return props 

login_key = "VkDmDqKHbXj4++InKEdC+EubUuqd9hoYXsaSlG7sk34="
backend =  "tianyan176-2"

tianyan_props = tianyan_machine_config(login_key, backend)
print(type(tianyan_props))
print(tianyan_props)    
with open('tianyan176-2_props.json', 'w', encoding='utf-8') as f:
    # 两种写方式
    json.dump(tianyan_props, f, indent=3)
    # json.dump(wukong_props, f, indent=4, separators=(',', ':'))

with open('tianyan176-2_props.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(data)
#print(type(data))  # 输出 &lt;class 'dict'&gt;