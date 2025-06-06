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
st.title("网络监控数据可视化工具（时间归一化）")

uploaded_files = st.file_uploader("上传多个CSV文件（表头需一致）", type="csv", accept_multiple_files=True)

if uploaded_files:
    dfs = {}
    for file in uploaded_files:
        df = pd.read_csv(file)
        df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['datetime'])

        # ✅ 时间归一化为 delta_seconds
        df['delta_seconds'] = (df['datetime'] - df['datetime'].min()).dt.total_seconds()

        dfs[file.name] = df

    # 获取可选择字段
    common_columns = set.intersection(*[set(df.columns) for df in dfs.values()])
    numeric_fields = [col for col in common_columns if col not in ['timestamp', 'datetime', 'delta_seconds']]

    selected_fields = st.multiselect("选择要对比的字段", numeric_fields)

    if selected_fields:
        for field in selected_fields:
            st.subheader(f"字段对比：{field}（X轴：归一化秒数）")
            fig, ax = plt.subplots(figsize=(12, 4))
            for name, df in dfs.items():
                ax.plot(df['delta_seconds'], df[field], label=name)
            ax.set_xlabel("时间（秒）")
            ax.set_ylabel(field)
            ax.set_title(f"{field} 对比趋势（时间归一化）")
            ax.legend()
            ax.grid(True)
            st.pyplot(fig)

            # 导出按钮
            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            st.download_button(
                label=f"导出 {field} 图像",
                data=buf.getvalue(),
                file_name=f"{field}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png"
            )
