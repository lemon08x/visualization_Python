import tkinter as tk
from tkinter import ttk
from Collect.collect_data import MonitorApp
from Present import withGUI

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("主界面 - 选择功能")
        self.root.geometry("300x150")

        ttk.Label(root, text="请选择功能：", font=('Helvetica', 14)).pack(pady=20)

        ttk.Button(root, text="WebSocket数据测试", width=20, command=self.open_monitor_ui).pack(pady=5)
        ttk.Button(root, text="数据可视化", width=20, command=self.open_other_ui).pack(pady=5)

    def open_monitor_ui(self):
        top = tk.Toplevel(self.root)
        MonitorApp(top)  # 显示监控界面

    def open_other_ui(self):
        top = tk.Toplevel(self.root)
        withGUI.MultiFilePlotterApp(top)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
