import os
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import logging

# 设置 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========================= 数据读取函数 =========================

def read_ue_info(key, num=25, grp='', beg=0, path="data"):
    """从CSV文件读取UE性能数据并预处理"""
    dat = []

    # 循环读取num个CSV文件
    for n in range(1, num + 1 - beg + 1):
        csv_file = os.path.join(path, key, f"query-{grp}{beg - 1 + n}.csv")
        logger.info(f"Reading file: {csv_file}")

        if not os.path.exists(csv_file):
            logger.warning(f"File not found: {csv_file}")
            break

        # 读取CSV文件
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded DataFrame with shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")

        def get_field(name):
            """从数据框提取特定字段的数据"""
            field_df = df[df['_field'] == name].reset_index(drop=True)
            logger.debug(f"Field '{name}' rows: {len(field_df)}")
            return field_df

        try:
            ue_info = pd.DataFrame({
                't': get_field('ri')['_time'],
                'ri': pd.to_numeric(get_field('ri')['_value'], errors='coerce'),
                'cqi': pd.to_numeric(get_field('cqi')['_value'], errors='coerce'),
                'dl_mcs': pd.to_numeric(get_field('dl_mcs')['_value'], errors='coerce'),
                'dl_brate': pd.to_numeric(get_field('dl_brate')['_value'], errors='coerce'),
                'dl_nof_ok': pd.to_numeric(get_field('dl_nof_ok')['_value'], errors='coerce'),
                'dl_nof_nok': pd.to_numeric(get_field('dl_nof_nok')['_value'], errors='coerce'),
                'ul_mcs': pd.to_numeric(get_field('ul_mcs')['_value'], errors='coerce'),
                'ul_nof_ok': pd.to_numeric(get_field('ul_nof_ok')['_value'], errors='coerce'),
                'ul_nof_nok': pd.to_numeric(get_field('ul_nof_nok')['_value'], errors='coerce')
            })
        except Exception as e:
            logger.error(f"Failed to parse fields: {e}")
            continue

        res = ue_info[ue_info['dl_brate'] > 0].copy()
        res['dl_pct_nok'] = res['dl_nof_nok'] / (res['dl_nof_ok'] + res['dl_nof_nok'])
        logger.info(f"Filtered rows with dl_brate > 0: {len(res)}")
        dat.append(res)

    return dat

# ========================= 热力图数据生成 =========================

def ue_values(key, cfg=(40, 5), coln='dl_brate'):
    out = []
    bgn = np.arange(0, cfg[0]+1, cfg[1])
    num = 25

    for tag in bgn:
        logger.info(f"Processing tag: {tag}")
        tmp_data = read_ue_info(key, num, f"{tag}.")
        tx_gain = np.linspace(80, 80 - 2.5 * (num - 1), num)

        val = [np.mean(d[coln]) if not d.empty else 0 for d in tmp_data[:num]]
        val += [0] * (num - len(val))
        logger.debug(f"Values for tag {tag}: {val}")

        out.append(pd.DataFrame({
            'col': tx_gain,
            'row': [tag] * num,
            'val': val
        }))

    return pd.concat(out, ignore_index=True)

# ========================= 矩阵数据生成 =========================

def ue_matrix(key, cfg=(40, 5), coln='dl_brate'):
    bgn = np.arange(0, cfg[0]+1, cfg[1])
    num = 25
    mat = np.zeros((len(bgn), num))

    for i, tag in enumerate(bgn):
        logger.info(f"Matrix row for tag: {tag}")
        tmp_data = read_ue_info(key, num, f"{tag}.")
        val = [np.mean(d[coln]) if not d.empty else 0 for d in tmp_data[:num]]
        val += [0] * (num - len(val))
        logger.debug(f"Matrix values: {val}")
        mat[i, :] = val

    return mat

# ========================= 热力图绘制函数 =========================

def plot_heatmap(out_df, zmax=160e6, title="", annotate_pos=None):
    fig = go.Figure(data=go.Heatmap(
        x=out_df['col'],
        y=out_df['row'],
        z=out_df['val'],
        zmax=zmax,
        colorscale='Viridis',
        showscale=False
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(title="tx_gain (db)", autorange='reversed'),
        yaxis=dict(title="noise (db)")
    )
    if annotate_pos:
        fig.add_annotation(x=annotate_pos, y=0, text=f"Min {annotate_pos}", showarrow=True, font=dict(color="white"))
    return fig

# ========================= 三维面图绘制函数 =========================

def plot_surface(mat, cfg, num):
    fig = go.Figure(data=[
        go.Surface(
            x=np.linspace(80, 80 - 2.5 * (num - 1), num),
            y=np.arange(0, cfg[0]+1, cfg[1]),
            z=mat,
            showscale=False
        )
    ])
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="tx_gain (db)", autorange='reversed'),
            yaxis=dict(title="noise (db)"),
            zaxis=dict(title="dl_brate or dl_mcs")
        )
    )
    return fig

# ========================= 等高线图绘制函数 =========================

def plot_contour(mat, cfg, num):
    fig = go.Figure(data=go.Contour(
        x=np.linspace(80, 80 - 2.5 * (num - 1), num),
        y=np.arange(0, cfg[0]+1, cfg[1]),
        z=mat,
        contours=dict(start=0, end=160e6, size=30e6),
        colorscale='Viridis',
        showscale=False
    ))
    fig.update_layout(
        xaxis=dict(title="tx_gain (db)", autorange='reversed'),
        yaxis=dict(title="noise (db)")
    )
    return fig

# ========================= 数据处理函数 =========================

def generate_model_data(models, col='dl_brate', cfg=(40, 5), num=25):
    """
    为所有模型生成数据和矩阵
    :param models: 模型列表
    :param col: 数据列名
    :param cfg: 噪声配置(范围,步长)
    :param num: UE数量
    :return: 包含所有模型数据的字典
    """
    model_data = {}

    for model, name in models:
        logger.info(f"Processing model: {model} - {name}")

        # 生成原始数据
        out_df = ue_values(model, cfg, col)

        # 生成矩阵数据
        mat = ue_matrix(model, cfg, col)

        # 计算最小有效tx_gain
        tx_gain_all = np.linspace(80, 80 - 2.5 * (num - 1), num)
        nonzero_cols = np.sum(mat, axis=0) != 0
        valid_tx_gain = tx_gain_all[nonzero_cols]
        min_tx_gain = np.min(valid_tx_gain) if len(valid_tx_gain) > 0 else 0

        # 存储所有相关数据
        model_data[model] = {
            'name': name,
            'out_df': out_df,
            'mat': mat,
            'min_tx_gain': min_tx_gain
        }

    return model_data


# ========================= 绘图函数 =========================

def create_combined_plot(model_data):
    """
    创建包含所有模型热力图的组合图表
    :param model_data: 包含所有模型数据的字典
    :return: 组合图表对象
    """
    import plotly.subplots as sp

    # 获取模型列表
    models = list(model_data.keys())
    model_names = [model_data[model]['name'] for model in models]

    # 创建2×2的子图布局
    fig = sp.make_subplots(
        rows=2,
        cols=2,
        subplot_titles=model_names,
        vertical_spacing=0.15,  # 纵向间距
        horizontal_spacing=0.1  # 横向间距
    )

    # 为每个模型添加热力图
    for i, model in enumerate(models):
        data = model_data[model]
        row = i // 2 + 1  # 行位置(1或2)
        col = i % 2 + 1  # 列位置(1或2)

        # 创建热力图
        heatmap = go.Heatmap(
            x=data['out_df']['col'],
            y=data['out_df']['row'],
            z=data['out_df']['val'],
            zmax=160e6,  # 统一最大颜色值
            colorscale='Viridis',  # 统一颜色映射
            showscale=(i == 0)  # 只在第一个子图显示颜色条
        )

        # 添加到子图
        fig.add_trace(heatmap, row=row, col=col)

        # 添加最小值标注
        if not np.isnan(data['min_tx_gain']):
            fig.add_annotation(
                x=data['min_tx_gain'],
                y=0,
                text=f"Min: {data['min_tx_gain']:.1f}dB",
                showarrow=True,
                font=dict(color="white", size=10),
                row=row,
                col=col
            )

        # 设置坐标轴标签
        # 第一列设置y轴标签
        if col == 1:
            fig.update_yaxes(title_text="noise (db)", row=row, col=col)

        # 最后一行设置x轴标签
        if row == 2:
            fig.update_xaxes(
                title_text="tx_gain (db)",
                autorange='reversed',  # x轴反向
                row=row,
                col=col
            )

    # 设置全局布局
    fig.update_layout(
        height=800,  # 图表高度
        width=1000,  # 图表宽度
        title_text="UE Performance Comparison",
        title_x=0.5,  # 标题居中
        margin=dict(t=100, b=80, l=80, r=80),  # 页边距
        coloraxis=dict(
            colorscale='Viridis',
            colorbar=dict(
                title="dl_brate (bps)",  # 颜色条标题
                len=0.75,  # 颜色条长度
                thickness=15,  # 颜色条厚度
                x=1.01  # 位置调整
            )
        ),
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="RebeccaPurple"
        )
    )

    # 更新子图标题样式
    for i in range(len(models)):
        fig.layout.annotations[i].update(
            font=dict(size=14, color='darkblue')
        )

    return fig


# ========================= 主函数入口 =========================

def main():
    # 定义要比较的模型
    models = [
        ("scan_x200p", "vivo x200pro"),
        ("scan_x8p", "oppo find x8 pro"),
        ("scan_mi15", "xiaomi 15"),
        ("scan_m7p", "honor magic7 pro")
    ]

    # 生成模型数据
    model_data = generate_model_data(models)

    # 创建组合图表
    fig = create_combined_plot(model_data)

    # 显示图表
    fig.show()


if __name__ == "__main__":
    main()