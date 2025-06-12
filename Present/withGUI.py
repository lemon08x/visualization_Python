import sys
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import rcParams
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from io import BytesIO
import win32clipboard
from PIL import Image

# 中文支持
rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

from Feature import parse_complex_csv, plot_with_matplotlib, plot_with_seaborn, plot_with_plotly

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

        # 绘图方式选择
        tk.Label(control_frame, text="绘图方式：", font=('Arial', 12)).pack(pady=10)
        self.plot_backend_var = tk.StringVar(value="matplotlib")
        self.plot_backend_selector = ttk.Combobox(control_frame, textvariable=self.plot_backend_var,
                                                  values=["matplotlib", "seaborn", "plotly"], state="readonly")
        self.plot_backend_selector.pack()
        self.plot_backend_selector.bind("<<ComboboxSelected>>", lambda e: self.update_plot())

        # 图表列数选择
        tk.Label(control_frame, text="图表列数：", font=('Arial', 12)).pack(pady=10)
        self.col_count_var = tk.StringVar(value="1")  # 默认1列
        self.col_selector = ttk.Combobox(control_frame, textvariable=self.col_count_var, values=["1", "2", "3", "4"],
                                         state="readonly")
        self.col_selector.pack()
        self.col_selector.bind("<<ComboboxSelected>>", lambda e: self.update_plot())

        # # 绑定 trace 方法
        # self.col_count_var.trace("w", lambda *args: self.update_plot())

        # 添加 x 轴选择下拉框
        tk.Label(control_frame, text="选择 X 轴列：", font=('Arial', 12)).pack(pady=10)
        self.x_axis_var = tk.StringVar(value="delta_seconds")  # 默认使用 delta_seconds
        self.x_axis_selector = ttk.Combobox(control_frame, textvariable=self.x_axis_var, state="readonly")
        self.x_axis_selector.pack()
        self.x_axis_selector.bind("<<ComboboxSelected>>", lambda e: self.update_plot())

        # # 添加导出按钮
        # tk.Button(control_frame, text="导出图片", command=self.export_plot).pack(pady=10)
        # tk.Button(control_frame, text="复制到剪切板", command=self.copy_plot_to_clipboard).pack(pady=5)

        # 添加导出和复制按钮的水平布局
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="导出图片", command=self.export_plot).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="复制到剪切板", command=self.copy_plot_to_clipboard).pack(side=tk.LEFT, padx=5)

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
                df = parse_complex_csv(file_path)
                self.all_data[file_name] = df
                self.available_fields.update(df.columns.difference(['timestamp', 'datetime', 'delta_seconds']))
            except Exception as e:
                messagebox.showerror("读取失败", f"{file_name} 解析失败：{e}")

        # 更新 x 轴选择下拉框的选项
        if self.all_data:
            sample_df = next(iter(self.all_data.values()))
            self.x_axis_selector['values'] = list(sample_df.columns)
            if self.x_axis_var.get() not in sample_df.columns:
                self.x_axis_var.set("timestamp")  # 默认值

        self.update_checkboxes()
        self.update_plot()

    def clear_files(self):
        self.all_data.clear()
        self.available_fields.clear()
        self.update_checkboxes()
        self.update_plot()

    def export_plot(self):
        if not self.all_data:
            messagebox.showwarning("警告", "没有可导出的数据！")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300)
                messagebox.showinfo("成功", f"图片已成功保存到：{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"图片保存失败：{e}")

    def copy_plot_to_clipboard(self):
        if not self.all_data:
            messagebox.showwarning("警告", "没有可复制的图像！")
            return

        try:
            # 保存当前图像到 BytesIO 对象
            buf = BytesIO()
            self.fig.savefig(buf, format='png', dpi=300)
            buf.seek(0)

            # 使用 PIL 打开并转换为 RGB 模式
            image = Image.open(buf).convert("RGB")

            # 转换为 bitmap 数据
            output = BytesIO()
            image.save(output, 'BMP')
            data = output.getvalue()[14:]  # BMP 文件头的前 14 个字节需要去除
            output.close()

            # 设置剪贴板内容为图片
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()

            messagebox.showinfo("成功", "图像已复制到剪贴板！")

        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{e}")

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
            n_cols = 2

        x_axis_column = self.x_axis_var.get()
        backend = self.plot_backend_var.get()

        try:
            if backend == "matplotlib":
                plot_with_matplotlib(self.fig, self.all_data, selected, x_axis_column, n_cols)
            elif backend == "seaborn":
                plot_with_seaborn(self.fig, self.all_data, selected, x_axis_column, n_cols)
            elif backend == "plotly":
                plot_with_plotly(self.fig, self.all_data, selected, x_axis_column, n_cols)
                return
            else:
                messagebox.showerror("错误", f"未知绘图方式：{backend}")
                return

            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("绘图失败", f"发生错误：{e}")


if __name__ == '__main__':
    root = tk.Tk()

    def on_closing():
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    app = MultiFilePlotterApp(root)
    root.mainloop()
