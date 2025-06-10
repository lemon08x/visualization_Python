import os
import pandas as pd
import numpy as np
import plotly.graph_objs as go
# import plotly.express as px
import logging

# 设置 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========================= 数据读取函数 =========================

def read_ue_info(key, num=25, grp='', beg=0, path="data"):
    # path = os.path.expanduser(path)
    dat = []
    for n in range(1, num + 1 - beg + 1):
        csv_file = os.path.join(path, key, f"query-{grp}{beg - 1 + n}.csv")
        logger.info(f"Reading file: {csv_file}")

        if not os.path.exists(csv_file):
            logger.warning(f"File not found: {csv_file}")
            break

        df = pd.read_csv(csv_file)
        logger.info(f"Loaded DataFrame with shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")

        def get_field(name):
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

# ========================= 主函数入口 =========================

def main():
    col = 'dl_brate'
    cfg = (40, 5)
    num = 25

    models = [
        ("scan_x200p", "vivo x200pro"),
        ("scan_x8p", "oppo find x8 pro"),
        ("scan_mi15", "xiaomi 15"),
        ("scan_m7p", "honor magic7 pro")
    ]

    figs = []
    for model, name in models:
        logger.info(f"Processing model: {model} - {name}")
        out = ue_values(model, cfg, col)
        mat = ue_matrix(model, cfg, col)

        tx_gain_all = np.linspace(80, 80 - 2.5 * (num - 1), num)
        nonzero_cols = np.sum(mat, axis=0) != 0
        valid_tx_gain = tx_gain_all[nonzero_cols]
        min_col = np.min(valid_tx_gain) if len(valid_tx_gain) > 0 else 0

        fig = plot_heatmap(out, zmax=160e6, title=name, annotate_pos=min_col)
        figs.append(fig)

    for fig in figs:
        fig.show()

if __name__ == "__main__":
    main()
