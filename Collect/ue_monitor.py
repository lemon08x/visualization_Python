#!/usr/bin/env python3
import websocket
import json
import time
from datetime import datetime
import threading
import pandas as pd
import argparse
import sys
import paramiko

# Define all possible columns for the CSV file to ensure consistency.
CSV_HEADER = [
    'timestamp', 'ue_id', 'RAT', 'instant_rate_mbps', 'avg_rate_mbps', 'total_dl_bytes',
    'epre', 'ul_path_loss', 'p_ue', 'ul_phr', 'pucch1_snr', 'pusch_snr',
    'cqi', 'ri', 'dl_mcs', 'ul_mcs', 'ul_n_layer', 'ul_rank', 'dl_retx',
    'ul_retx', 'dl_err', 'ul_err', 'gain_4g', 'gain_5g', 'noise'
]

class UEMonitor:
    # def __init__(self, ws_url, output_file, time_limit=None, ssh_host=None, ssh_user=None, ssh_pass=None, nr_lte_switch=False, elevator_switch=False, noise_switch=False):
    def __init__(self, ws_url, output_file, time_limit=None, ssh_host=None, ssh_user=None, ssh_pass=None,
                 nr_lte_switch=False, elevator_switch=False, noise_switch=False, heatmap_test=False):
        self.ws_url = ws_url
        self.output_file = output_file
        self.time_limit = time_limit
        self.start_time = None
        self.data = []
        self.ws = None
        self.running = False
        # Dictionary to store the last state (bytes, time) for each UE to calculate average rate.
        self.ue_states = {}
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass
        self.ssh_client = None
        self.ssh_channel = None
        self.nr_lte_switch = nr_lte_switch
        self.elevator_switch = elevator_switch
        self.noise_switch = noise_switch
        self.heatmap_test = heatmap_test  # 新增测试标志
        self.gain_4g = 0
        self.gain_5g = 0
        self.noise = None
        if self.nr_lte_switch:
            # Hardcoded parameters for the NR-LTE switch test
            self.g5_steady_time = 30
            self.g5_decline_time = 40
            self.overlap_time = 20
            self.g4_incline_time = 40
            self.g4_steady_time = 30
            # Total time is 30+40+40+30-20 = 120s, but we will run until 4g steady time is over.
            # Start of 4G incline: (30 + 40 - 20) = 50s. End of 4G incline: 50 + 40 = 90s.
            # End of test: 90 + 30 = 120s
            self.total_switch_time = self.g5_steady_time + self.g5_decline_time + self.g4_incline_time + self.g4_steady_time - self.overlap_time
            if self.time_limit is None:
                self.time_limit = self.total_switch_time
        elif self.elevator_switch:
            # Hardcoded parameters for the elevator simulation
            self.elevator_total_time = 120
            self.elevator_in_time = 50
            self.elevator_out_time = 70
            self.g5_high_gain = 90
            self.g5_low_gain = 40
            if self.time_limit is None:
                self.time_limit = self.elevator_total_time
        elif self.noise_switch:
            # Hardcoded parameters for the noise switch test
            self.noise_steady_time = 10
            self.noise_incline_time = 100
            self.total_noise_time = 120
            self.noise_max = 0
            self.noise_min = -50
            if self.time_limit is None:
                self.time_limit = self.total_noise_time
        elif self.heatmap_test:
            # 新增：热力图测试的网格参数
            self.noise_grid = [-50, -40, -30, -20, -10, 0]  # Y轴：噪声等级
            self.gain_grid = [90, 80, 70, 60, 50, 40, 30, 20]  # X轴：信号增益等级
            self.dwell_time = 10  # 每个(增益,噪声)点的驻留测量时间（秒）

            # 计算总测试时间
            self.total_test_time = len(self.noise_grid) * len(self.gain_grid) * self.dwell_time
            if self.time_limit is None:
                self.time_limit = self.total_test_time

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'ue_list' in data and data['ue_list']:
                timestamp = datetime.now()
                for ue in data['ue_list']:
                    # Use 'ran_ue_id' for 5G/NR and 'enb_ue_id' for 4G/LTE, as requested.
                    if 'ran_ue_id' in ue:
                        self._process_nr_ue(ue, timestamp)
                    elif 'enb_ue_id' in ue:
                        self._process_lte_ue(ue, timestamp)
                    # Silently ignore UEs that don't have a recognized ID.
            
        except json.JSONDecodeError:
            print(f"Error decoding message: {message}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)
            print(f"Message content: {message}", file=sys.stderr)

    def _process_nr_ue(self, ue, timestamp):
        ue_id = ue['ran_ue_id']
        
        # Safely get the first cell, or an empty dict if it doesn't exist.
        cell = ue.get('cells', [{}])[0]
        
        # Calculate total DL bytes from all QoS flows for 5G.
        total_dl_bytes = 0
        if 'qos_flow_list' in ue:
            for qos_flow in ue['qos_flow_list']:
                if isinstance(qos_flow, dict):
                    total_dl_bytes += int(qos_flow.get('dl_total_bytes', 0))

        avg_rate_mbps = self._calculate_avg_rate(ue_id, total_dl_bytes, timestamp)
        
        record = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'ue_id': ue_id,
            'RAT': 'NR',
            'instant_rate_mbps': cell.get('dl_bitrate', 0) / 1_000_000,
            'avg_rate_mbps': avg_rate_mbps,
            'total_dl_bytes': total_dl_bytes,
            'epre': cell.get('epre'),
            'ul_path_loss': cell.get('ul_path_loss'),
            'p_ue': cell.get('p_ue'),
            'ul_phr': cell.get('ul_phr'),
            'pusch_snr': cell.get('pusch_snr'),
            'cqi': cell.get('cqi'),
            'ri': cell.get('ri'),
            'dl_mcs': cell.get('dl_mcs'),
            'ul_mcs': cell.get('ul_mcs'),
            'ul_n_layer': cell.get('ul_n_layer'),
            'ul_rank': cell.get('ul_rank'),
            'dl_retx': cell.get('dl_retx'),
            'ul_retx': cell.get('ul_retx'),
            'dl_err': cell.get('dl_err'),
            'ul_err': cell.get('ul_err'),
            'pucch1_snr': None, # This field is specific to 4G/LTE.
            'gain_4g': self.gain_4g,
            'gain_5g': self.gain_5g,
            'noise': self.noise,
        }
        self.data.append(record)
        print(f"Logged NR UE[{ue_id}] data at {timestamp.strftime('%H:%M:%S')}")

    def _process_lte_ue(self, ue, timestamp):
        ue_id = ue['enb_ue_id']
        
        cell = ue.get('cells', [{}])[0]
        
        # For 4G, get total DL bytes from the ERAB list.
        total_dl_bytes = 0
        if 'erab_list' in ue and ue['erab_list']:
            for erab in ue['erab_list']:
                dl_bytes = erab.get('dl_total_bytes', 0)
                if dl_bytes > 0:
                    total_dl_bytes = dl_bytes
                    break
        
        avg_rate_mbps = self._calculate_avg_rate(ue_id, total_dl_bytes, timestamp)
        
        record = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'ue_id': ue_id,
            'RAT': 'LTE',
            'instant_rate_mbps': cell.get('dl_bitrate', 0) / 1_000_000,
            'avg_rate_mbps': avg_rate_mbps,
            'total_dl_bytes': total_dl_bytes,
            'epre': cell.get('epre'),
            'ul_path_loss': cell.get('ul_path_loss'),
            'p_ue': cell.get('p_ue'),
            'pucch1_snr': cell.get('pucch1_snr'),
            'pusch_snr': cell.get('pusch_snr'),
            'cqi': cell.get('cqi'),
            'dl_mcs': cell.get('dl_mcs'),
            'ul_mcs': cell.get('ul_mcs'),
            'ul_n_layer': cell.get('ul_n_layer'),
            # These fields are specific to 5G/NR.
            'ul_phr': None, 'ri': None, 'ul_rank': None, 'dl_retx': None,
            'ul_retx': None, 'dl_err': None, 'ul_err': None,
            'gain_4g': self.gain_4g,
            'gain_5g': self.gain_5g,
            'noise': self.noise,
        }
        self.data.append(record)
        print(f"Logged LTE UE[{ue_id}] data at {timestamp.strftime('%H:%M:%S')}")
        
    def _calculate_avg_rate(self, ue_id, current_bytes, timestamp):
        avg_rate = 0
        if ue_id in self.ue_states:
            last_state = self.ue_states[ue_id]
            time_diff = (timestamp - last_state['time']).total_seconds()
            if time_diff > 0:
                bytes_diff = current_bytes - last_state['bytes']
                if bytes_diff >= 0:
                    avg_rate = (bytes_diff * 8) / (time_diff * 1_000_000) # Mbps
        
        # Update state for the current UE
        self.ue_states[ue_id] = {'bytes': current_bytes, 'time': timestamp}
        return avg_rate

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}", file=sys.stderr)

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed.")

    def on_open(self, ws):
        print("WebSocket connection opened.")
        request = {
            "stats": True,
            "message": "ue_get",
            "message_id": "ue_monitor_script"
        }
        self.ws.send(json.dumps(request))

    def start_iperf(self):
        if not all([self.ssh_host, self.ssh_user, self.ssh_pass]):
            print("SSH credentials not provided, skipping iperf.")
            return

        try:
            print(f"Connecting to {self.ssh_user}@{self.ssh_host}...")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.ssh_host, username=self.ssh_user, password=self.ssh_pass, timeout=10)

            print("Starting iperf...")
            iperf_command = "iperf -c 192.168.2.2 -u -b 230m -t 1000 -i 1\n"

            self.ssh_channel = self.ssh_client.invoke_shell()
            self.ssh_channel.send(iperf_command)
            print("iperf command sent.")
            # A small delay to allow the command to start and shell to be ready.
            time.sleep(1)

        except Exception as e:
            print(f"Failed to start iperf: {e}", file=sys.stderr)
            if self.ssh_client:
                self.ssh_client.close()
            self.ssh_client = None
            self.ssh_channel = None

    def _nr_lte_switch_loop(self):
        """A loop to control NR-LTE gain switching."""
        print("NR-LTE switch test started.")
        switch_start_time = time.time()

        while self.running:
            elapsed_time = time.time() - switch_start_time

            if elapsed_time > self.total_switch_time:
                print("NR-LTE switch test finished.")
                break

            # Timeline calculation
            t = elapsed_time
            g5_steady_end = self.g5_steady_time
            g5_decline_end = g5_steady_end + self.g5_decline_time
            g4_incline_start = g5_decline_end - self.overlap_time
            g4_incline_end = g4_incline_start + self.g4_incline_time

            # Calculate 5G gain
            if t < g5_steady_end:
                self.gain_5g = 90
            elif t < g5_decline_end:
                self.gain_5g = 90 * (g5_decline_end - t) / self.g5_decline_time
            else:
                self.gain_5g = 0

            # Calculate 4G gain
            if t < g4_incline_start:
                self.gain_4g = 45
            elif t < g4_incline_end:
                self.gain_4g = 45 * (t - g4_incline_start) / self.g4_incline_time + 45
            else: # 4G steady period
                self.gain_4g = 90
            
            self.gain_4g = round(self.gain_4g)
            self.gain_5g = round(self.gain_5g)

            # Send gain update via WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                gain_msg = {
                    "message": "rf_gain",
                    "rx_gain": [self.gain_4g, self.gain_5g, self.gain_5g],
                    "tx_gain": [self.gain_4g, self.gain_5g, self.gain_5g],
                    "message_id": 20
                }
                self.ws.send(json.dumps(gain_msg))
            
            time.sleep(1)

    def _elevator_switch_loop(self):
        """A loop to control gain for elevator simulation."""
        print("Elevator simulation test started.")
        switch_start_time = time.time()

        while self.running:
            elapsed_time = time.time() - switch_start_time

            if elapsed_time > self.elevator_total_time:
                print("Elevator simulation test finished.")
                break
            
            self.gain_4g = 0

            if self.elevator_in_time <= elapsed_time < self.elevator_out_time:
                self.gain_5g = self.g5_low_gain
            else:
                self.gain_5g = self.g5_high_gain

            # Send gain update via WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                gain_msg = {
                    "message": "rf_gain",
                    "rx_gain": [self.gain_4g, self.gain_5g, self.gain_5g],
                    "tx_gain": [self.gain_4g, self.gain_5g, self.gain_5g],
                    "message_id": 20
                }
                self.ws.send(json.dumps(gain_msg))
            
            time.sleep(1)

    def _noise_switch_loop(self):
        """A loop to control noise for the noise switch test."""
        print("Noise switch test started.")
        switch_start_time = time.time()

        while self.running:
            elapsed_time = time.time() - switch_start_time

            if elapsed_time > self.total_noise_time:
                print("Noise switch test finished.")
                break

            # Timeline calculation
            t = elapsed_time
            noise_incline_start = self.noise_steady_time
            noise_incline_end = noise_incline_start + self.noise_incline_time
            
            noise_level = 0
            if t < noise_incline_start:
                noise_level = self.noise_min
            elif t < noise_incline_end:
                progress = (t - noise_incline_start) / self.noise_incline_time
                noise_level = self.noise_min + progress * (self.noise_max - self.noise_min)
            else:
                noise_level = self.noise_max
            
            self.noise = round(noise_level, 2)

            # Send noise update via WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                noise_msg = {
                    "noise_level": self.noise,
                    "channel": 2,
                    "message": "noise_level",
                    "message_id": "ENB_noise_level_"
                }
                self.ws.send(json.dumps(noise_msg))
            
            time.sleep(1)

    def _heatmap_test_loop(self):
        """新增：步进-保持-测量模式，用于热力图数据采集"""
        print("Heatmap data collection test started.")

        # 外层循环：遍历噪声等级 (Y轴)
        for noise_level in self.noise_grid:
            if not self.running: break

            # 设置当前噪声值
            self.noise = noise_level
            print(f"\n===== Setting Noise Level to: {self.noise} dB =====")
            if self.ws and self.ws.sock and self.ws.sock.connected:
                noise_msg = {"noise_level": self.noise, "channel": 2, "message": "noise_level",
                             "message_id": "heatmap_noise"}
                self.ws.send(json.dumps(noise_msg))

            # 内层循环：遍历信号增益等级 (X轴)
            for gain_level in self.gain_grid:
                if not self.running: break

                # 设置当前的4G和5G增益
                self.gain_4g = gain_level
                self.gain_5g = gain_level
                print(f"--- Testing point (Gain: {gain_level}, Noise: {noise_level}) for {self.dwell_time}s ---")

                if self.ws and self.ws.sock and self.ws.sock.connected:
                    gain_msg = {
                        "message": "rf_gain", "rx_gain": [self.gain_4g, self.gain_5g, self.gain_5g],
                        "tx_gain": [self.gain_4g, self.gain_5g, self.gain_5g], "message_id": "heatmap_gain"
                    }
                    self.ws.send(json.dumps(gain_msg))

                # 在此(增益,噪声)点上驻留，让主循环持续抓取数据
                time.sleep(self.dwell_time)

        print("Heatmap data collection finished.")
        self.stop_monitoring()

    def stop_iperf(self):
        if self.ssh_channel:
            try:
                print("Stopping iperf...")
                # Send Ctrl+C
                self.ssh_channel.send('\x03')
                self.ssh_channel.close()
                print("iperf stopped.")
            except Exception as e:
                print(f"Error stopping iperf: {e}", file=sys.stderr)

        if self.ssh_client:
            self.ssh_client.close()
            print("SSH connection closed.")

    def start_monitoring(self):
        self.start_iperf()
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
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()

        if self.nr_lte_switch:
            switch_thread = threading.Thread(target=self._nr_lte_switch_loop, daemon=True)
            switch_thread.start()
        elif self.elevator_switch:
            switch_thread = threading.Thread(target=self._elevator_switch_loop, daemon=True)
            switch_thread.start()
        elif self.noise_switch:
            switch_thread = threading.Thread(target=self._noise_switch_loop, daemon=True)
            switch_thread.start()
        elif self.heatmap_test:
            switch_thread = threading.Thread(target=self._heatmap_test_loop, daemon=True)
            switch_thread.start()

        try:
            while self.running:
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    request = {
                        "stats": True,
                        "message": "ue_get",
                        "message_id": "ue_monitor_script"
                    }
                    self.ws.send(json.dumps(request))
                
                if self.time_limit and (time.time() - self.start_time) >= self.time_limit:
                    print(f"\nTime limit of {self.time_limit} seconds reached.")
                    self.stop_monitoring()
                    return
                    
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_monitoring()

    def stop_monitoring(self):
        print("\nStopping monitoring...")
        self.running = False
        if self.ws:
            self.ws.close()
        self.stop_iperf()
        self.save_data()

    def save_data(self):
        if not self.data:
            print("No data collected, not writing file.")
            return

        print(f"\nSaving {len(self.data)} records to {self.output_file}...")
        df = pd.DataFrame(self.data)
        
        # Reorder columns according to the header and fill missing with None.
        df = df.reindex(columns=CSV_HEADER)
        
        try:
            df.to_csv(self.output_file, index=False)
            print("Save complete.")
        except Exception as e:
            print(f"Error saving data to CSV: {e}", file=sys.stderr)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Monitor 4G/5G UE parameters via WebSocket and log to CSV.')
    parser.add_argument('--ws-url', type=str, default="ws://127.0.0.1:9001/",
                      help='WebSocket server URL (default: ws://127.0.0.1:9001/)')
    parser.add_argument('-t', '--time-limit', type=int, help='Time limit in seconds for monitoring.')
    parser.add_argument('-o', '--output-file', type=str, default='ue_monitor_log.csv',
                      help='Output CSV file name (default: ue_monitor_log.csv)')
    parser.add_argument('--ssh-host', type=str, default="192.168.50.66", help='SSH host IP.')
    parser.add_argument('--ssh-user', type=str, default="sdr", help='SSH username.')
    parser.add_argument('--ssh-pass', type=str, default="123123", help='SSH password.')
    parser.add_argument('--nr-lte-switch', action='store_true',
                        help='Enable NR-LTE switch test with dynamic gain control.')
    parser.add_argument('--elevator-switch', action='store_true',
                        help='Enable elevator simulation with dynamic gain control.')
    parser.add_argument('--noise-switch', action='store_true',
                        help='Enable noise switch test.')
    parser.add_argument('--heatmap-test', action='store_true',
                        help='Enable heatmap data collection test.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    monitor = UEMonitor(args.ws_url, args.output_file, args.time_limit,
                        args.ssh_host, args.ssh_user, args.ssh_pass,
                        args.nr_lte_switch, args.elevator_switch, args.noise_switch, args.heatmap_test)

    print("Starting UE monitoring...")
    if args.time_limit:
        print(f"Monitoring will automatically stop after {args.time_limit} seconds.")
    print("Press Ctrl+C to stop.")
    monitor.start_monitoring()

if __name__ == "__main__":
    main() 