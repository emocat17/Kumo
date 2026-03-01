"""
共享工具模块 - 提供日志清理等公共功能
"""
import os
import re
import datetime
from core.logging import get_logger

logger = get_logger(__name__)


def clean_ansi(text: str) -> str:
    """Remove ANSI escape sequences and special characters from text"""
    if not text:
        return text
    
    # Remove standard ANSI escape sequences (colors, cursor movement, etc.)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    # Remove backspace characters (退格键)
    text = re.sub(r'[\x08\x7F]+', '', text)
    # Remove carriage return characters that cause duplicate lines
    text = text.replace('\r', '')
    return text


def is_progress_only_line(line: str) -> bool:
    """Check if a line is only progress bar characters"""
    if not line:
        return True
    
    # Remove common characters that appear in progress bars
    cleaned = line.replace('|', '').replace('/', '').replace('-', '').replace('\\', '').replace(' ', '')
    # Also remove timestamp-like patterns [YYYY-MM-DD HH:MM:SS]
    cleaned = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', '', cleaned)
    cleaned = cleaned.strip()
    return len(cleaned) == 0


def get_log_dir(subdir: str = "install"):
    """获取日志目录路径"""
    log_dir = os.path.abspath(os.path.join(os.getcwd(), "logs", subdir))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir


def append_log(log_file: str, message: str, add_timestamp: bool = True):
    """
    通用日志写入函数
    
    Args:
        log_file: 日志文件完整路径
        message: 日志消息
        add_timestamp: 是否添加时间戳
    """
    if not message:
        return
    
    # Clean ANSI sequences from message
    message = clean_ansi(message)
    
    # Skip empty or whitespace-only lines
    if not message.strip():
        return
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            # Split by actual newlines
            lines = message.split('\n')
            for line in lines:
                line = line.strip()
                # Skip empty lines and progress-only lines
                if line and not is_progress_only_line(line):
                    if add_timestamp:
                        f.write(f"[{timestamp}] {line}\n")
                    else:
                        f.write(f"{line}\n")
    except Exception as e:
        logger.error(f"Error writing log: {e}")
