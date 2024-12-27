import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础目录
BASE_DIR = Path(__file__).parent
ADMIN_PLUGINS_DIR = BASE_DIR / "admin"
LISTEN_PLUGINS_DIR = BASE_DIR / "listen"

# Telegram API 配置
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 管理员ID列表
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_ID', '').split(',')]

# 数据存储
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

KEYWORDS_FILE = DATA_DIR / 'keywords.json'
SESSIONS_FILE = DATA_DIR / 'sessions.json'

def load_json(file_path: Path, default=None):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default if default is not None else {}

def save_json(file_path: Path, data):
    """保存JSON文件"""
    file_path.parent.mkdir(exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
