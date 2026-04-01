import requests
import json

def wukong_prop_to_chaoyue_prop(response):
    def get_coupling_map(response):
        gateJSON = response['gateJSON']
        result = []
        for key, value in gateJSON.items():
            if value['fidelity'] != '0.0':
                bits = key.split('_')
                if len(bits) != 2:
                    continue
                try:
                    bit1 = int(bits[0])
                    bit2 = int(bits[1])
                    result.append([bit1, bit2])
                except ValueError:
                    continue
        print(result)
        return result

    def str_to_float(s):
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
        
    def get_qubits_props(response):
        qubits_props = {}
        adjJSON = response['adjJSON']
        qubitNum = response['qubitNum']
        for i in range(qubitNum):
            qubit_str = str(i)
            if qubit_str not in qubits_props:
                qubits_props[qubit_str] = {}
            qubits_props[qubit_str]['index'] = int(qubit_str)
            qubits_props[qubit_str]['t1'] = str_to_float(adjJSON[qubit_str]['T1'])
            qubits_props[qubit_str]['t2'] = str_to_float(adjJSON[qubit_str]['T2'])
            qubits_props[qubit_str]['readout_error'] = 1 - str_to_float(adjJSON[qubit_str]['ReadoutFidelity'])
            qubits_props[qubit_str]['frequency'] = str_to_float(adjJSON[qubit_str]['frequency'])
        return qubits_props
    def get_gate_props(response):
        gate_props = {}
        gateJSON = response['gateJSON']
        qubitNum = response['qubitNum']
        adjJSON = response['adjJSON']
        for i in range(qubitNum):
            gate_props['u3'+'_'+str(i)] = {}
            gate_props['u3'+'_'+str(i)]['index'] = 'u3'+'_'+str(i)
            gate_props['u3'+'_'+str(i)]['gate_error'] = 1- str_to_float(adjJSON[str(i)]['averageFidelity'])
        for key, value in gateJSON.items():
            gate_props['cz'+'_'+key] = {}
            gate_props['cz'+'_'+key]['index'] = 'cz'+'_'+key
            gate_props['cz'+'_'+key]['gate_error'] = 1- str_to_float(value['fidelity'])
        return gate_props
    wukong_props = {}
    wukong_props['name'] = "wukong"
    wukong_props['gates_set'] = ['u3', 'cz']
    wukong_props['num_qubits'] = response['qubitNum']
    wukong_props['coupling_map'] = get_coupling_map(response)
    wukong_props['qubits_props'] = get_qubits_props(response)
    wukong_props['gate_props'] = get_gate_props(response)

    return wukong_props

def get_wukong_prop():
    url = 'https://console.originqc.com.cn/api/taskApi/getFullConfig.json?chipId=72'
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception('Cannot make HTTP request。The status code is {}'.format(response.status_code))
    else:
        response = response.json()['obj']

    prop = wukong_prop_to_chaoyue_prop(response)
    return prop

wukong_props=get_wukong_prop()

with open('wukong_props.json', 'w', encoding='utf-8') as f:
    # 两种写方式
    json.dump(wukong_props, f, indent=3)
    # json.dump(wukong_props, f, indent=4, separators=(',', ':'))

with open('wukong_props.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(data)
#print(type(data))  # 输出 &lt;class 'dict'&gt;