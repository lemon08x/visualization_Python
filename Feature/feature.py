import pandas as pd
import logging
from datetime import datetime

from Feature.logging_config import configure_logging

# 调用 configure_logging 函数
configure_logging()

def fix_timestamp(ts):
    """
    修复时间戳格式，支持 MM:SS.ms 和 HH:MM:SS.ms 格式及其它
    """
    # 尝试直接解析为 MM:SS.ms
    parsed = pd.to_datetime(ts, format='%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    # 尝试解析为 HH:MM:SS.ms
    parsed = pd.to_datetime(ts, format='%H:%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    # 尝试解析为 YYYY-MM-DD HH:MM:SS.ffffff
    parsed = pd.to_datetime(ts, format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
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

    # 获取当前时间并格式化为字符串
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')

    # 将 DataFrame 保存到文件
    output_file = f'output/{current_time}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')

    # 计算delta_seconds
    if pd.api.types.is_datetime64_any_dtype(df['pd_time']):
        df['delta_seconds'] = (df['pd_time'] - df['pd_time'].min()).dt.total_seconds()
    else:
        logging.error("pd_time列未成功转换为datetime类型，无法计算delta_seconds")
        df['delta_seconds'] = None  # 或者其他处理方式

    # 添加Duration列
    df["Duration"] = range(len(df))

    return df