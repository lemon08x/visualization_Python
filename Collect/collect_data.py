# 文件名建议：5g_monitor_ui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from Collect.webSocket import UEMonitor5G

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("5G UE Monitor")

        # UE ID
        ttk.Label(root, text="UE ID:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.ue_id_entry = ttk.Entry(root)
        self.ue_id_entry.grid(row=0, column=1, padx=5, pady=5)

        # WS URL
        ttk.Label(root, text="WebSocket URL:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.ws_url_entry = ttk.Entry(root)
        self.ws_url_entry.insert(0, "ws://127.0.0.1:9001/")
        self.ws_url_entry.grid(row=1, column=1, padx=5, pady=5)

        # Time limit
        ttk.Label(root, text="Time Limit (s):").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.time_entry = ttk.Entry(root)
        self.time_entry.grid(row=2, column=1, padx=5, pady=5)

        # Buttons
        self.start_button = ttk.Button(root, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Log area
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=20)
        self.log_text.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Internal state
        self.monitor = None
        self.thread = None

    def start_monitoring(self):
        try:
            ue_id = int(self.ue_id_entry.get())
            ws_url = self.ws_url_entry.get()
            time_limit = self.time_entry.get()
            time_limit = int(time_limit) if time_limit else None
        except ValueError:
            messagebox.showerror("Input Error", "请输入有效的 UE ID 和时间")
            return

        self.log("Starting monitoring...")
        self.monitor = UEMonitor5G(ws_url, ue_id, time_limit)

        # 替换 print 函数为 log
        import builtins
        builtins.print = self.log

        self.thread = threading.Thread(target=self.monitor.start_monitoring)
        self.thread.start()

    def log(self, message):
        self.log_text.insert(tk.END, str(message) + "\n")
        self.log_text.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()
