def hex_to_bin(origin_result, measure_count):
    result = [
    	{bin(int(k.replace('0x', ''), 16))[2:].zfill(measure_count): v for k, v in d.items()}
    	for d in origin_result
		]
    return result


# 读取 OpenQASM 文件并统计 measure 操作次数
def count_measure_operations(content):
    # 按行分割并统计
    lines = content.split('\n')
    measure_count = 0

    for line in lines:
        if line.strip().startswith("measure"):  # 忽略空格并检查行首
            measure_count += 1
    return measure_count