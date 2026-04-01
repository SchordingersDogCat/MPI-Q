import matplotlib.pyplot as plt
import numpy as np

# 在非交互式环境强制使用Agg后端（避免警告）
plt.switch_backend('Agg')

def read_bit_waveform_data(filename):
    """从文件中读取比特波形数据，忽略行号"""
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # 跳过文件头
    data_lines = []
    for line in lines:
        if line.strip() and not line.startswith('data >'):
            data_lines.append(line.strip())
    
    # 读取比特个数（第一行）
    bit_count = int(data_lines[0].split()[-1])
    
    # 读取每个比特的数据个数（第二行）
    data_points_per_bit = list(map(int, data_lines[1].split()[1:1+bit_count]))
    
    # 读取波形数据（剩余行）
    waveforms = []
    for i in range(2, 2 + bit_count):
        if i < len(data_lines):
            data_line = data_lines[i].split()
            waveform_data = []
            for item in data_line:
                try:
                    waveform_data.append(float(item))
                except ValueError:
                    continue
            # 跳过行号（如果存在）
            if len(waveform_data) > 0 and waveform_data[0].is_integer() and waveform_data[0] <= 10:
                waveform_data = waveform_data[1:]
            waveforms.append(waveform_data)
    
    return bit_count, data_points_per_bit, waveforms

def plot_bit_waveforms(bit_count, data_points_per_bit, waveforms):
    """绘制比特波形图并保存为文件"""
    plt.figure(figsize=(12, 8))
    
    for i in range(bit_count):
        if i < len(waveforms):
            plt.subplot(bit_count, 1, i + 1)
            x = np.arange(len(waveforms[i]))
            plt.plot(x, waveforms[i], 'b-', linewidth=1.5, label=f'Bit {i+1}')
            plt.ylabel(f'Bit {i+1} Amplitude')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # 调整y轴范围
            y_min = min(waveforms[i])
            y_max = max(waveforms[i])
            y_range = y_max - y_min
            plt.ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)
    
    plt.xlabel('Sample Points')
    plt.suptitle('Bit Waveform Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # 保存为文件（替换plt.show()）
    output_path = "data_to_wave/serverdata_curves.png"  # 输出文件路径
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print("波形图已保存为: serverdata_curves.png")
    plt.close()  # 释放资源

def plot_combined_waveforms(bit_count, waveforms):
    """在同一图中绘制所有比特的波形并保存为文件"""
    plt.figure(figsize=(12, 6))
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    for i in range(bit_count):
        if i < len(waveforms):
            x = np.arange(len(waveforms[i]))
            color = colors[i % len(colors)]
            plt.plot(x, waveforms[i], color=color, linewidth=2, label=f'Bit {i+1}')
            plt.plot(x, waveforms[i], color=color, marker='o', markersize=3, alpha=0.7)
    
    plt.xlabel('Sample Points')
    plt.ylabel('Amplitude')
    plt.title('Combined Bit Waveforms')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    # 保存为文件（替换plt.show()）
    plt.savefig('bit_waveforms_combined.png', dpi=300, bbox_inches='tight')
    print("合并的波形图已保存为: bit_waveforms_combined.png")
    plt.close()

# 主程序
if __name__ == "__main__":
    filename = "data/all_qubits.txt"
    
    try:
        bit_count, data_points_per_bit, waveforms = read_bit_waveform_data(filename)
        
        print(f"比特个数: {bit_count}")
        print(f"每个比特的数据点数: {data_points_per_bit}")
        print("\n波形数据:")
        for i, waveform in enumerate(waveforms):
            print(f"Bit {i+1}: 长度={len(waveform)}, 数据={waveform[:5]}...")  # 简化输出
        
        # 绘制分开的波形图（保存为文件）
        plot_bit_waveforms(bit_count, data_points_per_bit, waveforms)
        
        # 可选：绘制合并的波形图（取消注释即可启用）
        # plot_combined_waveforms(bit_count, waveforms)
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filename}")
    except Exception as e:
        print(f"处理文件时出错: {e}")