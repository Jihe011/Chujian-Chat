"""
日志工具模块
提供日志记录功能
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

class LoggerConfig:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.log_dir = os.path.join(root_dir, "logs")
        self.api_log_dir = os.path.join(root_dir, "apilogs")
        self.ensure_log_dir()

    def ensure_log_dir(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        if not os.path.exists(self.api_log_dir):
            os.makedirs(self.api_log_dir)

    def get_api_log_file(self):
        current_date = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.api_log_dir, f"bot_{current_date}.log")

    def get_log_file(self):
        current_date = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"bot_{current_date}.log")

    def setup_logger(self, name: Optional[str] = None, level: int = logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = True
        
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            self.get_log_file(),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def cleanup_old_logs(self, days: int = 7):
        try:
            current_date = datetime.now()
            if not os.path.exists(self.log_dir):
                return
            for filename in os.listdir(self.log_dir):
                if not filename.startswith("bot_") or not filename.endswith(".log"):
                    continue
                
                file_path = os.path.join(self.log_dir, filename)
                file_date_str = filename[4:12]
                try:
                    file_date = datetime.strptime(file_date_str, "%Y%m%d")
                    days_old = (current_date - file_date).days
                    
                    if days_old > days:
                        os.remove(file_path)
                        print(f"已删除旧日志文件: {filename}")
                except ValueError:
                    continue
        except Exception as e:
            print(f"清理日志文件失败: {str(e)}")


def log_api_request(service_name: str, endpoint: str, request_data: dict):
    try:
        import json
        
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        api_log_dir = os.path.join(root_dir, "apilogs")
        
        if not os.path.exists(api_log_dir):
            os.makedirs(api_log_dir)
        
        current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(api_log_dir, f"bot_{current_date}.txt")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n{'='*80}\n"
        log_entry += f"时间: {timestamp}\n"
        log_entry += f"服务: {service_name}\n"
        log_entry += f"端点: {endpoint}\n"
        log_entry += f"请求数据:\n{json.dumps(request_data, ensure_ascii=False, indent=2)}\n"
        log_entry += f"{'='*80}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"记录API请求失败: {str(e)}")