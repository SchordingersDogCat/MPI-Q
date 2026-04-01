import numpy as np
import matplotlib.pyplot as plt

# 读取多行数据（每行作为独立数据集）
def read_line_data(file_path):
    try:
        data_lines = []
        with open(file_path, 'r') as file:
            for line in file:
                line_data = list(map(float, line.strip().split(',')))
                data_lines.append(line_data)
        return data_lines
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

# 绘制多子图曲线并保存为文件
def plot_subplots(data_lines):
    if not data_lines:
        print("No data to plot")
        return
    
    # 非交互式环境设置（避免警告）
    plt.switch_backend('Agg')  # 使用非交互式后端
    
    # 创建4个子图（2行2列布局）
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 10))
    fig.suptitle('Data Curves by Rows', fontsize=16)
    
    # 为每个子图绘制对应行的数据
    for i, ax in enumerate(axes.flat):
        if i < len(data_lines):
            data = data_lines[i]
            x = np.arange(len(data))
            
            ax.plot(x, data, marker='o', linestyle='-', 
                    color=plt.cm.Set3(i % 12),
                    markersize=4, linewidth=1.5)
            
            ax.set_title(f'Row {i+1} Data', fontsize=12)
            ax.set_xlabel('Index', fontsize=10)
            ax.set_ylabel('Value', fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.6)
    
    # 调整子图间距
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # 保存图表到文件（替换 plt.show()）
    output_path = "data_to_wave/carddata_curves.png"  # 输出文件路径
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved successfully to {output_path}")
    plt.close()  # 关闭图表释放资源

if __name__ == "__main__":
    file_path = "data/result1.txt"  # 确保此路径正确
    data_lines = read_line_data(file_path)
    
    if data_lines:
        print(f"Successfully read {len(data_lines)} rows of data")
        plot_subplots(data_lines)
    else:
        print("Failed to read data")