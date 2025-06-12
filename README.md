# Signal2025 Visualization - 多源5G数据可视化分析工具

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Tkinter](https://img.shields.io/badge/Tkinter-8.6+-green?logo=tkinter)
![MIT License](https://img.shields.io/github/license/mashape/apistatus.svg)

---

## 📝 项目简介

本项目是一套面向5G网络监控与信号分析的多源CSV数据可视化工具，支持数据采集、解析、对比分析与多种可视化方式。主要特性：

- 支持多CSV文件批量导入与字段级筛选、对比
- 内置Matplotlib/Seaborn/Plotly三种绘图引擎，支持交互式与静态可视化
- 提供基于Tkinter的桌面GUI和Streamlit的Web可视化界面
- 集成5G UE WebSocket实时数据采集与分析
- 适配多品牌5G终端实验数据的批量处理与热力图分析

---

## 📂 目录结构

```bash
├── Feature/                  # 核心功能模块
│   ├── __init__.py
│   ├── csv_parser.py         # CSV解析与时间戳处理
│   ├── plot_utils.py         # 多后端绘图工具
│   └── logging_config.py     # 日志配置
├── Collect/                  # 数据采集与WebSocket监控
│   ├── __init__.py
│   ├── collect_data.py       # Tkinter监控UI
│   └── webSocket.py          # 5G UE WebSocket采集核心
├── Present/                  # 可视化与Web界面
│   ├── __init__.py
│   ├── withGUI.py            # 多文件对比GUI（Tkinter）
│   ├── webGUI.py             # Streamlit Web可视化
│   ├── tryPandas.py          # Streamlit多图对比
│   └── firstVersion.py       # 早期可视化脚本
├── 5g_old/                   # 历史5G信号分析脚本
│   └── R_trans.py
├── data/                     # 输入CSV数据
├── output/                   # 输出结果（图表/中间文件）
├── ui_main.py                # 主界面入口（Tkinter）
├── requirements.txt          # 依赖包清单
└── README.md                 # 项目说明文档
```

---

## 🚀 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动桌面GUI**
   ```bash
   python ui_main.py
   ```

3. **启动Web可视化（Streamlit）**
   ```bash
   streamlit run Present/webGUI.py
   # 或
   streamlit run Present/tryPandas.py
   ```

4. **5G UE数据采集**
   - 通过桌面GUI或运行 `Collect/webSocket.py` 采集实时数据，自动保存为CSV。

---

## 🛠️ 主要功能模块

- **多文件字段对比可视化**：支持多CSV文件字段级对比，灵活选择X轴与字段，支持多种绘图后端。
- **5G UE实时监控**：通过WebSocket实时采集5G UE信号与速率数据，自动统计与可视化。
- **批量实验数据分析**：支持5G多终端实验数据的批量热力图、等高线、三维面图分析。
- **导出与复制**：支持图像导出PNG和一键复制到剪贴板。

---

## 📞 联系与贡献

如有建议或需求，欢迎提交Issue或PR！

---
