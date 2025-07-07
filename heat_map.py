import pandas as pd
import numpy as np
import argparse
import sys
import os
import plotly.graph_objs as go

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
    fig = go.Figure(data=go.Heatmap(
        x=df['gain_5g'],
        y=df['noise'],
        z=df[metric],
        colorscale='Viridis',
        colorbar=dict(title=f'{metric.replace("_", " ").title()}')
    ))
    fig.update_layout(
        title='原始数据点热力图',
        xaxis=dict(title='信号增益 (Gain)', autorange='reversed'),
        yaxis=dict(title='噪声等级 (Noise)'),
        width=900,
        height=700
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
    pivot = df.pivot_table(index='noise_bin', columns='gain_bin', values=metric, aggfunc='mean', fill_value=0)
    z = pivot.values
    x = pivot.columns.values
    y = pivot.index.values

    # 自动设置等高线间隔
    z_min = np.nanmin(z)
    z_max = np.nanmax(z)
    n_levels = 12
    if z_max > z_min:
        interval = (z_max - z_min) / n_levels
    else:
        interval = 1
    if interval > 1:
        interval = 10 ** np.floor(np.log10(interval))
    if interval > 1 and (z_max - z_min) / interval < 6:
        interval = interval / 2

    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()

    # 找到最小有效tx_gain
    col_sum = np.sum(z, axis=0)
    valid_x = x[col_sum != 0]
    min_tx_gain = valid_x.min() if len(valid_x) > 0 else None

    # 画contour主图
    fig = go.Figure(data=go.Contour(
        x=x,
        y=y,
        z=z,
        contours=dict(
            start=float(z_min),
            end=float(z_max),
            size=float(interval)
        ),
        colorscale='Viridis',
        showscale=True,
        name='All Data'
    ))

    # 叠加LTE/NR点
    df_lte = df[df['RAT'] == 'LTE']
    df_nr = df[df['RAT'] == 'NR']
    if not df_lte.empty:
        fig.add_trace(go.Scatter(
            x=df_lte['gain_5g'],
            y=df_lte['noise'],
            mode='markers',
            marker=dict(color='red', symbol='x', size=8, line=dict(width=1, color='white')),
            name='LTE'
        ))
    if not df_nr.empty:
        fig.add_trace(go.Scatter(
            x=df_nr['gain_5g'],
            y=df_nr['noise'],
            mode='markers',
            marker=dict(color='blue', symbol='circle-open', size=8, line=dict(width=1, color='blue')),
            name='NR'
        ))

    fig.update_layout(
        xaxis=dict(title="tx_gain (db)", autorange='reversed', range=[x_max, x_min]),
        yaxis=dict(title="noise (db)", range=[y_min, y_max]),
        title=title,
        width=900, height=700
    )
    # 添加注释
    if min_tx_gain is not None:
        fig.add_annotation(
            x=min_tx_gain, y=y_min,
            text=f"Min {min_tx_gain}",
            font=dict(size=14, color="#FFF"),
            arrowcolor="#FFF", ax=0
        )
    fig.add_annotation(
        x=x_min + (x_max-x_min)*0.1, y=y_max, text=title,
        font=dict(size=14, color="#FFF"), showarrow=False
    )
    if output_file:
        fig.write_image(output_file)
        print(f"\n拟合等高线图已保存至: {output_file}")
    else:
        fig.show()

def create_optimized_heatmap(input_file: str, output_file: str = None, metric: str = DEFAULT_METRIC):
    required_columns = ['gain_5g', 'noise', 'RAT', metric]
    df= validate_input_file(input_file, required_columns)
    if metric not in df.columns:
        metric = 'instant_rate_mbps'

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='生成原始与拟合的网络性能热力图 (交互式plotly)',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input_file', type=str, help='由 ue_monitor_old.py 生成的CSV数据文件路径。')
    parser.add_argument('-o', '--output', type=str, help='热力图保存路径 (如: heatmap.png/pdf/svg)。')
    parser.add_argument('-m', '--metric', type=str, default=DEFAULT_METRIC, help=f'可视化的性能指标 (默认: {DEFAULT_METRIC})')
    args = parser.parse_args()

    create_optimized_heatmap(args.input_file, args.output, args.metric)
