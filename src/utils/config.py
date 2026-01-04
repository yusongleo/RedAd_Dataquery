import os
import sys
import json
from pathlib import Path

# ========================================================
# 动态获取项目根目录
# 逻辑：兼容 PyCharm 源码运行环境与 PyInstaller 打包后的 EXE 环境
# ========================================================
if getattr(sys, 'frozen', False):
    # 打包环境：sys.executable 指向 exe 文件，其父目录为程序所在文件夹
    BASE_DIR = Path(sys.executable).parent
else:
    # 开发环境：当前文件位于 src/utils/，向上回溯 3 层至项目根目录
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ========================================================
# 定义各配置文件与数据目录的绝对路径
# ========================================================
APP_CONFIG_PATH = BASE_DIR / 'app_config.json'
TOKEN_CONFIG_PATH = BASE_DIR / 'token_config.json'
DATA_DOWNLOAD_DIR = BASE_DIR / 'data_download'
FEISHU_CONFIG_PATH = BASE_DIR / 'feishu_config.json'

# 确保存储目录存在
DATA_DOWNLOAD_DIR.mkdir(exist_ok=True)

def load_json(path: Path) -> dict | list:
    """通用 JSON 读取器，处理文件不存在或格式错误的情况"""
    if not path.exists():
        # token_config 默认为空列表，其他默认为空字典
        return [] if 'token_config' in str(path) else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return [] if 'token_config' in str(path) else {}

def save_json(path: Path, data: dict | list) -> None:
    """通用 JSON 写入器，支持中文编码"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_app_config() -> dict:
    """加载聚光平台应用配置 (App ID / Secret)"""
    config = load_json(APP_CONFIG_PATH)
    if not config or 'APP_ID' not in config:
        raise FileNotFoundError(f"❌ 无法加载 app_config.json，程序查找路径: {APP_CONFIG_PATH}")
    return config

def load_feishu_config() -> dict:
    """加载飞书应用配置"""
    config = load_json(FEISHU_CONFIG_PATH)
    required_keys = ['app_id', 'app_secret']
    if not config or any(k not in config for k in required_keys):
        return {}
    return config