import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from io import BytesIO
from datetime import datetime
import math

# 中文支持
rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

st.set_page_config(layout="wide")
st.title("网络监控数据可视化工具（字段对比 + 多图）")

uploaded_files = st.file_uploader("上传多个CSV文件（表头需一致）", type="csv", accept_multiple_files=True)

if uploaded_files:
    dfs = {}
    for file in uploaded_files:
        df = pd.read_csv(file)
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

        df = df.dropna(subset=['datetime'])
        df['delta_seconds'] = (df['datetime'] - df['datetime'].min()).dt.total_seconds()
        dfs[file.name] = df

    # 找出共同字段（排除非数值列）
    common_columns = set.intersection(*[set(df.columns) for df in dfs.values()])
    numeric_fields = [col for col in common_columns if pd.api.types.is_numeric_dtype(next(iter(dfs.values()))[col])]

    x_axis_options = ['timestamp', 'datetime', 'delta_seconds']
    available_x_axis = [x for x in x_axis_options if x in common_columns or x == 'delta_seconds']
    x_axis = st.selectbox("选择 X 轴字段", available_x_axis, index=available_x_axis.index('delta_seconds') if 'delta_seconds' in available_x_axis else 0)

    selected_fields = st.multiselect("选择要对比的字段", [col for col in numeric_fields if col not in x_axis_options])

    col_count = st.selectbox("每行图表列数", [1, 2, 3, 4], index=1)  # 默认 2 列

    if selected_fields:
        n_cols = int(col_count)
        n_rows = math.ceil(len(selected_fields) / n_cols)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 4*n_rows), squeeze=False)
        axes = axes.flatten()

        for idx, field in enumerate(selected_fields):
            ax = axes[idx]
            for name, df in dfs.items():
                if field in df.columns:
                    ax.plot(df[x_axis], df[field], marker='o', markersize=2, alpha=0.7, label=name)
            ax.set_title(field)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(field)
            ax.legend(fontsize='small')
            ax.grid(True)

        # 隐藏多余子图
        for j in range(len(selected_fields), len(axes)):
            fig.delaxes(axes[j])

        fig.tight_layout()
        st.pyplot(fig)

        # 下载图像
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300)
        st.download_button(
            label=f"导出全部字段图像",
            data=buf.getvalue(),
            file_name=f"all_fields_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png"
        )
