import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
matplotlib.use('TkAgg')  # Set the backend to Agg

# Set a font that supports Chinese characters
rcParams['font.sans-serif'] = ['SimHei']  # Use SimHei or another CJK-compatible font
rcParams['axes.unicode_minus'] = False   # Ensure minus signs are displayed correctly

from feature import parse_complex_csv

def plot_rate_trends(df, output_file='output/rate_trends.png'):
    """
    可视化网络速率和总字节数趋势
    """
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 速率曲线
    ax[0].plot(df['noise_level'], df['instant_rate'], 'b-', label='实时速率')
    ax[0].plot(df['noise_level'], df['avg_rate'], 'r--', label='平均速率')
    ax[0].set_ylabel('速率 (Mbps)')
    ax[0].legend()
    ax[0].grid(True)
    ax[0].set_title('网络速率监控')

    # 总字节曲线
    ax[1].plot(df['noise_level'], df['total_bytes'], 'g-', label='总字节数')
    ax[1].set_ylabel('字节总量')
    ax[1].set_xlabel('时间')
    ax[1].legend()
    ax[1].grid(True)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.show()


if __name__ == '__main__':
    # 输入路径
    input_file = '../data/huawei_ue_1_monitor_5g.csv'

    # 解析CSV并获取DataFrame
    df = parse_complex_csv(input_file)

    # 将 DataFrame 保存到文件
    output_file = '../output/ue_28_monitor_5g_saved.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')

    print("当前 DataFrame 列名：", df.columns.tolist())

    # 可视化
    plot_rate_trends(df)
