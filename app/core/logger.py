import logging
from logging.handlers import RotatingFileHandler
import os
import psutil

# 创建日志目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__) 

def log_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # 获取更详细的内存信息
    memory_details = {
        'rss': memory_info.rss / 1024 / 1024,  # 物理内存
        'vms': memory_info.vms / 1024 / 1024,  # 虚拟内存
        'shared': getattr(memory_info, 'shared', 0) / 1024 / 1024,  # 共享内存
        'percent': process.memory_percent()  # 内存使用百分比
    }
    
    logger.info(
        f"Memory usage: {memory_details['rss']:.2f} MB (Physical), "
        f"{memory_details['vms']:.2f} MB (Virtual), "
        f"{memory_details['shared']:.2f} MB (Shared), "
        f"{memory_details['percent']:.1f}% of total"
    ) 