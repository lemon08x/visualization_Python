import pandas as pd
import numpy as np
import argparse
import sys
import glob
import os
import plotly.graph_objs as go
from typing import Optional

# ---- 全局常量设置 ----
DEFAULT_METRIC = 'avg_rate_mbps'


def validate_input_file(input_file, required_columns):
    if not os.path.isfile(input_file):
        print(f"错误: 文件 '{input_file}' 不存在。", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(input_file)
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"错误: 缺少列: {missing}", file=sys.stderr)
        sys.exit(1)
    df_clean = df.dropna(subset=required_columns).copy()
    if df_clean.empty:
        print("错误: 清理后无有效数据。", file=sys.stderr)
        sys.exit(1)
    return df_clean

def create_grid(df, x_col='gain_5g', y_col='noise', resolution=400):
    x_min, x_max = df[x_col].min(), df[x_col].max()
    y_min, y_max = df[y_col].min(), df[y_col].max()
    grid_x, grid_y = np.mgrid[x_min:x_max:complex(resolution), y_min:y_max:complex(resolution)]
    return (x_min, x_max, y_min, y_max), grid_x, grid_y

def plot_raw_heatmap(df, metric, output_file=None):
    z = df[metric]
    z_min = z.min()
    z_max = z.max()

    custom_colorscale = [
        [0.0, "#0c0180"],
        [0.1, "#1101bc"],
        [0.2, "#1a2dff"],
        [0.3, "#247ef2"],
        [0.4, "#21d9cc"],
        [0.5, "#2ad921"],
        [0.6, "#abd921"],
        [0.7, "#f2cc24"],
        [0.8, "#f27324"],
        [0.9, "#e52222"],
        [1.0, "#e52222"]
    ]
    # 归一化z
    normed_z = (z - z_min) / (z_max - z_min) if z_max > z_min else z*0
    fig = go.Figure(data=go.Heatmap(
        x=df['gain_5g'],
        y=df['noise'],
        z=z,
        zmin=z_min,
        zmax=z_max,
        colorscale="viridis",
        colorbar=dict(title=f'{metric.replace("_", " ").title()}')
    ))
    fig.update_layout(
        title='原始数据点热力图',
        xaxis=dict(title='信号增益 (Gain)', autorange='reversed'),
        yaxis=dict(title='噪声等级 (Noise)'),
        width=2400,
        height=1600
    )
    if output_file:
        fig.write_image(output_file)
        print(f"\n原始数据点热力图已保存至: {output_file}")
    else:
        fig.show()

def plot_fitted_heatmap(df, metric, output_file=None, title="拟合等高线图"):
    # 设定步长
    gain_step = 2.5
    noise_step = 5

    # 计算bin
    df['gain_bin'] = (df['gain_5g'] / gain_step).round() * gain_step
    df['noise_bin'] = (df['noise'] / noise_step).round() * noise_step

    # 生成规则网格（所有数据）
    pivot = df.pivot_table(index='noise_bin', columns='gain_bin', values=metric, aggfunc='mean')

    z = pivot.values
    x = pivot.columns.values
    y = pivot.index.values

    # 自动设置等高线分级，使z_max一端的区间宽度为其它的两倍
    z_min = np.nanmin(z)
    z_max = np.nanmax(z)
    n_levels = 10  # 总区间数

    col_sum = np.sum(z, axis=0)
    # 计算列的有效性
    valid_cols = col_sum != 0

    # 严格筛选有效数据
    x = pivot.columns[valid_cols]
    z = z[:, valid_cols]
    x_min, x_max = x.min(), x.max()
    print(f"[DEBUG] x_min: {x_min}, x_max: {x_max}")
    y_min, y_max = y.min(), y.max()

    # 找到最小z值的位置
    min_z_idx = np.unravel_index(np.argmin(z, axis=None), z.shape)
    min_z_x = x[min_z_idx[1]]
    min_z_y = y[min_z_idx[0]]
    min_z_val = z[min_z_idx]

    # 色带
    custom_colorscale = [
        [0.0, "#0c0180"],
        [0.1, "#1101bc"],
        [0.2, "#1a2dff"],
        [0.3, "#247ef2"],
        [0.4, "#21d9cc"],
        [0.5, "#2ad921"],
        [0.6, "#abd921"],
        [0.7, "#f2cc24"],
        [0.8, "#f27324"],
        [0.9, "#e52222"],
        [1.0, "#e52222"]
    ]

    # # 构造新的 colorscale: 最小值绿色，最大值红色，其余用 Viridis
    # custom_colorscale = [
    #     [0.0, "green"],
    #     [0.0001, viridis[0][1]],
    #     *viridis[1:-1],
    #     [0.9999, viridis[-1][1]],
    #     [1.0, "red"]
    # ]

    # 色带比例点
    scale_positions = [c[0] for c in custom_colorscale][:-1]

    # 将比例映射到实际数值
    tickvals = [10 + p * 200 for p in scale_positions]

    # 格式化显示文本（可选：四舍五入，避免太长的小数）
    ticktext = [f"{val:.0f}" for val in tickvals]

    fig = go.Figure(data=go.Contour(
        x=x,
        y=y,
        z=z,
        contours=dict(
            start=float(10),
            end=float(210),
            size=float((200) / n_levels),
            coloring='fill',
            showlines=False
        ),
        colorscale=custom_colorscale,
        showscale=True,
        name='All Data',
        colorbar = dict(
            title='',  # 如果色带也有标题，可以在这里设置
            tickvals=tickvals,  # ✅ 强制 tick 在交界位置
            ticktext=ticktext,  # ✅ 对应的文本
            tickfont=dict(
                family="Manrope Medium",
                size=36
            )
        )
    ))

    # # 叠加LTE/NR点
    # df_lte = df[df['RAT'] == 'LTE']
    # df_nr = df[df['RAT'] == 'NR']
    # if not df_lte.empty:
    #     fig.add_trace(go.Scatter(
    #         x=df_lte['gain_5g'],
    #         y=df_lte['noise'],
    #         mode='markers',
    #         marker=dict(color='red', symbol='x', size=8, line=dict(width=1, color='white')),
    #         name='LTE'
    #     ))
    # if not df_nr.empty:
    #     fig.add_trace(go.Scatter(
    #         x=df_nr['gain_5g'],
    #         y=df_nr['noise'],
    #         mode='markers',
    #         marker=dict(color='blue', symbol='circle-open', size=8, line=dict(width=1, color='blue')),
    #         name='NR'
    #     ))

    fig.update_layout(
        xaxis=dict(
            title="TX_gain (dB)",
            range=[x_max, x_min],  # 直接设置倒序范围
            title_font=dict(size=44),  # <-- 设置X轴标题字体大小
            tickfont=dict(size=36),  # <-- 设置X轴刻度字体大小
            ticks = "outside",  # 将刻度线放在坐标轴外部
            ticklen = 10,  # 设置刻度线长度为10像素，这会推远刻度值
            tickwidth = 2  # 设置刻度线宽度
        ),
        yaxis=dict(
            title="Noise Level",
            range=[y_min, y_max],
            title_font=dict(size=44),  # <-- 设置Y轴标题字体大小
            tickfont=dict(size=36),  # <-- 设置Y轴刻度字体大小
            ticks = "outside",  # 将刻度线放在坐标轴外部
            ticklen = 10,  # 设置刻度线长度为10像素，这会推远刻度值
            tickwidth = 2  # 设置刻度线宽度
        ),
        title=None,
        font=dict(
            family="Manrope Medium"
        ),
        width=2400,
        height=1600
    )
    # 添加注释：标记最小z值
    # fig.add_annotation(
    #     x=min_z_x, y=min_z_y,
    #     text=f"Min z: {min_z_val:.2f}",
    #     font=dict(size=16, color="#fff"),  # 深色字体
    #     showarrow=True,
    #     arrowcolor="#222",  # 深色箭头
    #     arrowhead=2,
    #     ax=40, ay=-40,  # 箭头偏移
    #     bgcolor="#000",  # 白色背景
    #     bordercolor="#222",
    #     borderpad=4
    # )
    # 动态计算箭头偏移量，确保标记在图内
    # x轴是反向的（从大到小），y轴是正向的
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2

    # 如果最小值的x坐标在图的右半边（因为x轴反向，值更小），箭头就指向左
    ax_offset = -150 if min_z_x < x_center else 150
    # 如果最小值的y坐标在图的上半边，箭头就指向下
    ay_offset = 150 if min_z_y > y_center else -150

    # 添加注释：标记最小z值
    fig.add_annotation(
        x=min_z_x, y=min_z_y,
        text=f"Min z: {min_z_val:.2f}",
        font=dict(size=42, color="#000"),  # 根据您的要求设置字体颜色
        showarrow=True,
        arrowcolor="#fff",
        arrowwidth=4,
        arrowhead=2,
        ax=ax_offset,  # 使用动态计算的x偏移
        ay=ay_offset,  # 使用动态计算的y偏移
        bgcolor="#fff",  # 根据您的要求设置背景颜色
        bordercolor="#fff",
        borderpad=12
    )
    # fig.add_annotation(
    #     x=x_min + (x_max-x_min)*0.1, y=y_max, text=title,
    #     font=dict(size=14, color="#000"), showarrow=False
    # )
    if output_file:
        fig.write_image(output_file, width=2400, height=1600)
        print(f"\n拟合等高线图已保存至: {output_file}")
    else:
        fig.show()

def create_optimized_heatmap(input_file: str, output_file: Optional[str] = None, metric: str = DEFAULT_METRIC):
    required_columns = ['gain_5g', 'noise', 'RAT', metric]
    df= validate_input_file(input_file, required_columns)
    if metric not in df.columns:
        metric = 'instant_rate_mbps'

    # 只保留每组 (gain_5g, noise) 的最后10条数据
    df = df.sort_index()  # 保证原始顺序
    df = df.groupby(['gain_5g', 'noise'], as_index=False, group_keys=False).apply(lambda g: g.tail(10)).reset_index(drop=True)

    # 原始数据点热力图
    raw_out = None
    fit_out = None
    if output_file:
        # 自动生成两个文件名
        base, ext = os.path.splitext(output_file)
        raw_out = base + '_raw' + ext
        fit_out = base + '_fit' + ext
    print("\n生成原始数据点热力图...")
    plot_raw_heatmap(df, metric, raw_out)
    print("\n生成拟合+平滑热力图...")
    plot_fitted_heatmap(df, metric, fit_out)

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description='生成原始与拟合的网络性能热力图 (交互式plotly)',
#         formatter_class=argparse.RawTextHelpFormatter
#     )
#     parser.add_argument('input_file', type=str, help='由 ue_monitor_old.py 生成的CSV数据文件路径。')
#     parser.add_argument('-o', '--output', type=str, help='热力图保存路径 (如: heatmap.png/pdf/svg)。')
#     parser.add_argument('-m', '--metric', type=str, default=DEFAULT_METRIC, help=f'可视化的性能指标 (默认: {DEFAULT_METRIC})')
#     args = parser.parse_args()
#
#     create_optimized_heatmap(args.input_file, args.output, args.metric)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='批量生成多个文件的网络性能热力图。',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input_path', type=str,
                        help='单个CSV文件路径 或 包含多个CSV文件的文件夹路径。')
    parser.add_argument('-o', '--output', type=str,
                        help='热力图保存的文件夹路径 (可选)。\n如果未提供，图片将保存在输入文件相同的位置。')
    parser.add_argument('-m', '--metric', type=str, default=DEFAULT_METRIC,
                        help=f'可视化的性能指标 (默认: {DEFAULT_METRIC})')
    parser.add_argument('--ext', type=str, default='png',
                        help='输出图片的文件扩展名 (例如: png, pdf, svg)。\n默认: png')
    args = parser.parse_args()

    # --- 主要逻辑更新 ---

    # 1. 获取所有需要处理的输入文件列表
    if os.path.isdir(args.input_path):
        # 如果输入的是文件夹，则查找其中所有的.csv文件
        search_pattern = os.path.join(args.input_path, '*.csv')
        input_files = glob.glob(search_pattern)
        print(f"在文件夹 '{args.input_path}' 中找到 {len(input_files)} 个CSV文件。")
    elif os.path.isfile(args.input_path):
        # 如果输入的是单个文件，则将其放入列表以便统一处理
        input_files = [args.input_path]
    else:
        print(f"错误：提供的路径 '{args.input_path}' 不是一个有效的文件或文件夹。")
        exit(1)

    if not input_files:
        print("未找到任何需要处理的 .csv 文件。")
        exit(0)

    # 2. 确定输出目录
    output_dir = args.output
    if output_dir:
        # 如果指定了输出目录，则创建它（如果不存在）
        os.makedirs(output_dir, exist_ok=True)
        print(f"输出文件将保存到: {output_dir}")
    else:
        print("未指定输出目录，文件将保存在原位置。")

    # 3. 遍历每个文件并生成热力图
    for input_file in input_files:
        try:
            print(f"\n--- 正在处理: {os.path.basename(input_file)} ---")

            # 从输入文件名构建输出文件名
            # 例如：'path/to/data_part1.csv' -> 'data_part1'
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_filename = f"{base_name}.{args.ext}"

            if output_dir:
                # 指定了输出目录
                output_path = os.path.join(output_dir, output_filename)
            else:
                # 未指定，保存在输入文件旁边
                output_path = os.path.join(os.path.dirname(input_file), output_filename)

            # 调用你的核心函数生成图像
            create_optimized_heatmap(input_file, output_path, args.metric)

        except Exception as e:
            print(f"处理文件 {input_file} 时发生错误: {e}")

    print("\n所有文件处理完毕！")
