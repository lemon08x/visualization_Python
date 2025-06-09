import pandas as pd
import logging
import logging_config

# 配置日志
logging_config.configure_logging()

def fix_timestamp(ts):
    """
    修复时间戳格式，支持 MM:SS.ms 和 HH:MM:SS.ms 格式
    """
    # 尝试直接解析为 MM:SS.ms
    parsed = pd.to_datetime(ts, format='%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    # 尝试解析为 HH:MM:SS.ms
    parsed = pd.to_datetime(ts, format='%H:%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    # 记录无法解析的时间戳
    logging.warning(f"无法解析时间戳: {ts}")
    return None

def parse_complex_csv(file_path):
    """
    解析CSV文件，转换时间戳并返回DataFrame
    """
    # 读取CSV
    df = pd.read_csv(file_path)

    # 转换timestamp为pd_time
    df['pd_time'] = df['timestamp'].apply(fix_timestamp)

    # 删除转换失败的行（如果有）
    df = df.dropna(subset=['pd_time'])

    df['delta_seconds'] = (df['pd_time'] - df['pd_time'].min()).dt.total_seconds()

    return df