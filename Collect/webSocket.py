#!/usr/bin/env python3
import websocket
import json
import time
from datetime import datetime
import threading
import pandas as pd
import argparse
import matplotlib.pyplot as plt

class UEMonitor5G:
    def __init__(self, ws_url, ue_id, time_limit=None):
        self.ws_url = ws_url
        self.ue_id = ue_id
        self.time_limit = time_limit
        self.start_time = None
        self.data = []
        self.ws = None
        self.running = False
        self.last_bytes = 0
        self.last_time = None

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'ue_list' in data and len(data['ue_list']) > 0:
                ue = data['ue_list'][0]
                if 'cells' in ue and len(ue['cells']) > 0:
                    cell = ue['cells'][0]
                    
                    # 提取信号强度信息
                    signal_strength = {
                        'epre': cell.get('epre', 0),  # 参考信号接收功率
                        'ul_path_loss': cell.get('ul_path_loss', 0),  # 上行路径损耗
                        'p_ue': cell.get('p_ue', 0),  # UE发射功率
                        'ul_phr': cell.get('ul_phr', 0)  # 功率余量报告
                    }
                    
                    # 提取信号质量信息
                    signal_quality = {
                        'pusch_snr': cell.get('pusch_snr', 0),  # PUSCH信噪比
                        'cqi': cell.get('cqi', 0),  # 信道质量指示
                        'ri': cell.get('ri', 0)  # 秩指示
                    }
                    
                    # 提取调制编码信息
                    modulation_coding = {
                        'dl_mcs': cell.get('dl_mcs', 0),  # 下行调制编码方案
                        'ul_mcs': cell.get('ul_mcs', 0),  # 上行调制编码方案
                        'ul_n_layer': cell.get('ul_n_layer', 0),  # 上行MIMO层数
                        'ul_rank': cell.get('ul_rank', 0)  # 上行秩
                    }
                    
                    # 提取传输性能信息
                    dl_bitrate = cell.get('dl_bitrate', 0)
                    dl_bitrate_mbps = dl_bitrate / 1000000
                    
                    # 提取重传信息
                    retransmission = {
                        'dl_retx': cell.get('dl_retx', 0),  # 下行重传次数
                        'ul_retx': cell.get('ul_retx', 0),  # 上行重传次数
                        'dl_err': cell.get('dl_err', 0),  # 下行错误数
                        'ul_err': cell.get('ul_err', 0)  # 上行错误数
                    }
                    
                    timestamp = datetime.now()
                    
                    # 计算总字节数（从所有QoS Flow）
                    total_dl_bytes = 0
                    if 'qos_flow_list' in ue:
                        for qos_flow in ue['qos_flow_list']:
                            if isinstance(qos_flow, dict):
                                dl_bytes = qos_flow.get('dl_total_bytes', 0)
                                if isinstance(dl_bytes, (int, float)):
                                    total_dl_bytes += int(dl_bytes)
                    
                    # 计算平均速率
                    if self.last_bytes > 0 and self.last_time:
                        time_diff = (timestamp - self.last_time).total_seconds()
                        if time_diff > 0:
                            bytes_diff = total_dl_bytes - self.last_bytes
                            if bytes_diff >= 0:  # 确保字节差值为正
                                avg_rate = (bytes_diff * 8) / (time_diff * 1000000)  # 转换为Mbps
                            else:
                                avg_rate = 0
                        else:
                            avg_rate = 0
                    else:
                        avg_rate = 0
                    
                    # 更新上一次的值
                    self.last_bytes = total_dl_bytes
                    self.last_time = timestamp
                    
                    # 打印所有关键信息
                    print(f"{timestamp.strftime('%H:%M:%S')}: UE[{self.ue_id}]")
                    print(f"  Instant Rate: {dl_bitrate_mbps:.2f} Mbps, Avg Rate: {avg_rate:.2f} Mbps, Total DL: {total_dl_bytes/1024/1024:.2f} MB")
                    print(f"  Signal Strength: EPRE={signal_strength['epre']:.1f}dBm, Path Loss={signal_strength['ul_path_loss']:.1f}dB, P_UE={signal_strength['p_ue']:.1f}dBm")
                    print(f"  Signal Quality: PUSCH SNR={signal_quality['pusch_snr']:.1f}dB, CQI={signal_quality['cqi']}, RI={signal_quality['ri']}")
                    print(f"  Modulation Coding: DL MCS={modulation_coding['dl_mcs']:.1f}, UL MCS={modulation_coding['ul_mcs']}, UL Rank={modulation_coding['ul_rank']}")
                    print(f"  Retransmission: DL Retx={retransmission['dl_retx']}, UL Retx={retransmission['ul_retx']}")
                    print("  " + "-"*50)
                    
                    # 保存数据
                    self.data.append({
                        'timestamp': timestamp,
                        'instant_rate': dl_bitrate_mbps,
                        'avg_rate': avg_rate,
                        'total_bytes': total_dl_bytes,
                        **signal_strength,
                        **signal_quality,
                        **modulation_coding,
                        **retransmission
                    })
                    
        except json.JSONDecodeError:
            print(f"Error decoding message: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Message content: {message}")  # 添加消息内容打印，帮助调试

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_open(self, ws):
        request = {
            "ue_id": self.ue_id,
            "stats": True,
            "message": "ue_get",
            "message_id": "ENB_ue_get_"
        }
        ws.send(json.dumps(request))

    def start_monitoring(self):
        websocket.enableTrace(False)
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        self.running = True
        self.start_time = time.time()
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        try:
            while self.running:
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    request = {
                        "ue_id": self.ue_id,
                        "stats": True,
                        "message": "ue_get",
                        "message_id": "ENB_ue_get_"
                    }
                    self.ws.send(json.dumps(request))
                
                # 检查是否达到时间限制
                if self.time_limit and (time.time() - self.start_time) >= self.time_limit:
                    print(f"\nTime limit of {self.time_limit} seconds reached. Stopping monitoring...")
                    self.stop_monitoring()
                    return  # 添加 return 语句确保函数退出
                    
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            self.stop_monitoring()

    def stop_monitoring(self):
        print("\nStopping monitoring and generating plots...")
        self.running = False
        if self.ws:
            self.ws.close()
        self.save_data()  # 确保在停止时保存数据并生成图表

    def plot_data(self, df):
        # 创建图表
        plt.figure(figsize=(15, 10))
        
        # 将时间戳转换为字符串格式用于显示
        timestamps = [ts.strftime('%H:%M:%S') for ts in df['timestamp']]
        
        # 每10秒显示一个时间标签
        x_ticks = []
        x_labels = []
        for i, ts in enumerate(timestamps):
            if i % 10 == 0:  # 每10个数据点显示一个标签
                x_ticks.append(i)
                x_labels.append(ts)
        
        # 1. 网速变化图
        plt.subplot(2, 2, 1)
        plt.plot(range(len(df)), df['instant_rate'].values, label='Instant Rate')
        plt.plot(range(len(df)), df['avg_rate'].values, label='Average Rate')
        plt.title('Network Speed Over Time')
        plt.xlabel('Time')
        plt.ylabel('Speed (Mbps)')
        plt.xticks(x_ticks, x_labels, rotation=45)
        plt.legend()
        plt.grid(True)
        
        # 2. 信号强度与网速关系
        plt.subplot(2, 2, 2)
        plt.plot(range(len(df)), df['epre'].values, 'r-', label='EPRE')
        plt.title('EPRE Over Time')
        plt.xlabel('Time')
        plt.ylabel('EPRE (dBm)')
        plt.xticks(x_ticks, x_labels, rotation=45)
        plt.legend()
        plt.grid(True)
        
        # 3. 信号质量与网速关系
        plt.subplot(2, 2, 3)
        plt.plot(range(len(df)), df['cqi'].values, 'b-', label='CQI')
        plt.title('CQI Over Time')
        plt.xlabel('Time')
        plt.ylabel('CQI')
        plt.xticks(x_ticks, x_labels, rotation=45)
        plt.legend()
        plt.grid(True)
        
        # 4. 调制编码与网速关系
        plt.subplot(2, 2, 4)
        plt.plot(range(len(df)), df['dl_mcs'].values, 'g-', label='DL MCS')
        plt.title('DL MCS Over Time')
        plt.xlabel('Time')
        plt.ylabel('DL MCS')
        plt.xticks(x_ticks, x_labels, rotation=45)
        plt.legend()
        plt.grid(True)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(f'ue_{self.ue_id}_analysis_5g.png')
        print(f"\nAnalysis plots saved to ue_{self.ue_id}_analysis_5g.png")
        
        # 计算相关系数
        correlations = df[['instant_rate', 'epre', 'cqi', 'dl_mcs', 'pusch_snr', 'ul_path_loss', 'ri']].corr()
        print("\nCorrelation Matrix:")
        print(correlations['instant_rate'].sort_values(ascending=False))

    def save_data(self):
        if self.data:
            df = pd.DataFrame(self.data)
            filename = f'ue_{self.ue_id}_monitor_5g.csv'
            df.to_csv(filename, index=False)
            print(f"\nData saved to {filename}")
            
            if len(df) > 0:
                print(f"\nStatistics for UE[{self.ue_id}]:")
                print(f"Average Rate: {df['instant_rate'].mean():.2f} Mbps")
                print(f"Max Rate: {df['instant_rate'].max():.2f} Mbps")
                print(f"Min Rate: {df['instant_rate'].min():.2f} Mbps")
                print(f"Total Data: {df['total_bytes'].iloc[-1]/1024/1024:.2f} MB")
                print("\nSignal Statistics:")
                print(f"Average EPRE: {df['epre'].mean():.1f}dBm")
                print(f"Average Path Loss: {df['ul_path_loss'].mean():.1f}dB")
                print(f"Average CQI: {df['cqi'].mean():.1f}")
                print(f"Average DL MCS: {df['dl_mcs'].mean():.1f}")
                print(f"Average RI: {df['ri'].mean():.1f}")
                print("\nRetransmission Statistics:")
                print(f"Total DL Retransmissions: {df['dl_retx'].sum()}")
                print(f"Total UL Retransmissions: {df['ul_retx'].sum()}")
                print(f"Total DL Errors: {df['dl_err'].sum()}")
                print(f"Total UL Errors: {df['ul_err'].sum()}")
                
                # 绘制图表
                self.plot_data(df)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Monitor 5G UE throughput and signal parameters via WebSocket')
    parser.add_argument('--ue-id', type=int, required=True, help='UE ID to monitor')
    parser.add_argument('--ws-url', type=str, default="ws://127.0.0.1:9001/",
                      help='WebSocket server URL (default: ws://127.0.0.1:9001/)')
    parser.add_argument('-t', '--time-limit', type=int, help='Time limit in seconds for monitoring')
    return parser.parse_args()

def main():
    args = parse_arguments()
    monitor = UEMonitor5G(args.ws_url, args.ue_id, args.time_limit)
    
    try:
        print(f"Starting 5G UE[{args.ue_id}] monitoring...")
        if args.time_limit:
            print(f"Monitoring will automatically stop after {args.time_limit} seconds")
        print("Press Ctrl+C to stop")
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main() 
