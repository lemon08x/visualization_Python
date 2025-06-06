import sys
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import rcParams
import pandas as pd
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import math
import numpy as np

# 中文支持
rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False


def parse_csv(file_path):
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['datetime'], inplace=True)
    df['delta_seconds'] = (df['datetime'] - df['datetime'].min()).dt.total_seconds()
    return df


class MultiFilePlotterApp:
    def __init__(self, root):
        self.root = root
        self.all_data = {}  # {filename: DataFrame}
        self.selected_fields = {}
        self.available_fields = set()

        self.setup_ui()

    def setup_ui(self):
        self.root.title("多文件字段对比绘图")
        self.root.geometry("1400x900")

        # 左侧：控制面板
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Button(control_frame, text="添加CSV文件", command=self.load_files).pack(pady=10)
        tk.Button(control_frame, text="清除所有文件", command=self.clear_files).pack(pady=5)

        tk.Label(control_frame, text="选择字段：", font=('Arial', 12)).pack(pady=(10, 0))
        self.checkbuttons_frame = tk.Frame(control_frame)
        self.checkbuttons_frame.pack(fill=tk.Y, expand=True)

        # 图表列数选择
        tk.Label(control_frame, text="图表列数：", font=('Arial', 12)).pack(pady=10)
        self.col_count_var = tk.StringVar(value="1")  # 默认1列
        self.col_selector = ttk.Combobox(control_frame, textvariable=self.col_count_var, values=["1", "2", "3", "4"],
                                         state="readonly")
        self.col_selector.pack()
        self.col_selector.bind("<<ComboboxSelected>>", lambda e: self.update_plot())

        # 绑定 trace 方法
        self.col_count_var.trace("w", lambda *args: self.update_plot())

        # 右侧：绘图面板
        self.fig = plt.Figure(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def load_files(self):
        files = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if not files:
            return

        for file_path in files:
            file_name = file_path.split("/")[-1]
            try:
                df = parse_csv(file_path)
                self.all_data[file_name] = df
                self.available_fields.update(df.columns.difference(['timestamp', 'datetime', 'delta_seconds']))
            except Exception as e:
                messagebox.showerror("读取失败", f"{file_name} 解析失败：{e}")

        self.update_checkboxes()
        self.update_plot()

    def clear_files(self):
        self.all_data.clear()
        self.available_fields.clear()
        self.update_checkboxes()
        self.update_plot()

    def update_checkboxes(self):
        for widget in self.checkbuttons_frame.winfo_children():
            widget.destroy()

        self.selected_fields.clear()
        for col in sorted(self.available_fields):
            var = tk.IntVar()
            chk = tk.Checkbutton(self.checkbuttons_frame, text=col, variable=var, command=self.update_plot)
            chk.pack(anchor='w')
            self.selected_fields[col] = var

    def update_plot(self):
        selected = [field for field, var in self.selected_fields.items() if var.get()]
        self.fig.clf()

        if not selected or not self.all_data:
            self.canvas.draw()
            return

        try:
            n_cols = int(self.col_count_var.get())
        except ValueError:
            n_cols = 2  # fallback

        num_fields = len(selected)
        n_rows = math.ceil(num_fields / n_cols)

        # axes = self.fig.subplots(n_rows, n_cols, sharex=True)
        axes = np.array(self.fig.subplots(n_rows, n_cols, sharex=True)).flatten().tolist()


        for idx, field in enumerate(selected):
            ax = axes[idx]
            for file_name, df in self.all_data.items():
                if field in df.columns:
                    ax.plot(df['delta_seconds'], df[field], label=file_name)
            ax.set_title(field)
            ax.grid(True)
            ax.legend(fontsize='small')

        # 隐藏多余图
        for j in range(len(selected), len(axes)):
            self.fig.delaxes(axes[j])

        for ax in axes[-n_cols:]:
            ax.set_xlabel("时间（秒）")

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    root = tk.Tk()

    def on_closing():
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    app = MultiFilePlotterApp(root)
    root.mainloop()
