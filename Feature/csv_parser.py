# python
import os
import pandas as pd
import logging
from datetime import datetime
from Feature.logging_config import configure_logging

configure_logging()

def fix_timestamp(ts):
    """
    修复时间戳格式，支持 MM:SS.ms 和 HH:MM:SS.ms 格式及其它
    """
    parsed = pd.to_datetime(ts, format='%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    parsed = pd.to_datetime(ts, format='%H:%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    parsed = pd.to_datetime(ts, format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
    if not pd.isna(parsed):
        return parsed

    logging.warning(f"无法解析时间戳: {ts}")
    return None

def parse_complex_csv(file_path):
    """
    解析CSV文件，转换时间戳并返回DataFrame
    """
    df = pd.read_csv(file_path)
    df['pd_time'] = df['timestamp'].apply(fix_timestamp)

    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')

    # output_dir = 'output'
    # if not os.path.exists(output_dir):
    #     os.makedirs(output_dir)
    # output_file = f'{output_dir}/{current_time}.csv'
    # df.to_csv(output_file, index=False, encoding='utf-8')

    if pd.api.types.is_datetime64_any_dtype(df['pd_time']):
        df['delta_seconds'] = (df['pd_time'] - df['pd_time'].min()).dt.total_seconds()
    else:
        logging.error("pd_time列未成功转换为datetime类型，无法计算delta_seconds")
        df['delta_seconds'] = None

    df["Duration"] = range(len(df))
    return df