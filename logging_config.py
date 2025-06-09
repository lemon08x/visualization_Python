import logging

def configure_logging():
    """
    配置日志记录
    """
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')