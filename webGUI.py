import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from io import BytesIO
from datetime import datetime

# 中文支持
rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

st.set_page_config(layout="wide")
st.title("网络监控数据可视化工具")

uploaded_files = st.file_uploader("上传多个CSV文件（表头需一致）", type="csv", accept_multiple_files=True)

if uploaded_files:
    dfs = {}
    for file in uploaded_files:
        df = pd.read_csv(file)

        # 自动解析 datetime，并生成 delta_seconds
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

        if 'datetime' in df.columns:
            df = df.dropna(subset=['datetime'])
            df['delta_seconds'] = (df['datetime'] - df['datetime'].min()).dt.total_seconds()

        dfs[file.name] = df

    # 获取公共字段名
    common_columns = set.intersection(*[set(df.columns) for df in dfs.values()])

    x_axis = st.selectbox("选择 X 轴字段", sorted(common_columns))

    # 选出数值型字段（不包括X轴字段）
    numeric_fields = [
        col for col in common_columns
        if col != x_axis and pd.api.types.is_numeric_dtype(next(iter(dfs.values()))[col])
    ]

    selected_fields = st.multiselect("选择要对比的字段", numeric_fields)

    if selected_fields:
        for field in selected_fields:
            st.subheader(f"字段对比：{field}（X轴：{x_axis}）")
            fig, ax = plt.subplots(figsize=(12, 4))
            for name, df in dfs.items():
                if field in df.columns and x_axis in df.columns:
                    ax.plot(df[x_axis], df[field], label=name, marker='o', markersize=2, alpha=0.7)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(field)
            ax.set_title(f"{field} 对比趋势")
            ax.legend()
            ax.grid(True)
            st.pyplot(fig)

            # 下载按钮
            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            st.download_button(
                label=f"导出图像：{field}",
                data=buf.getvalue(),
                file_name=f"{field}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png"
            )
