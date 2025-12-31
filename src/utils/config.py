import os
import sys
import json
from pathlib import Path

# ========================================================
# [关键修改] 智能识别项目根目录
# ========================================================
if getattr(sys, 'frozen', False):
    # 如果是打包后的 EXE 环境
    # sys.executable 指向的是 RedAd_DataQuery.exe 文件的路径
    # 它的父目录就是 EXE 所在的文件夹
    BASE_DIR = Path(sys.executable).parent
else:
    # 如果是 PyCharm 源码开发环境
    # 保持原有的逻辑
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ========================================================

# 配置文件路径
APP_CONFIG_PATH = BASE_DIR / 'app_config.json'
TOKEN_CONFIG_PATH = BASE_DIR / 'token_config.json'
DATA_DOWNLOAD_DIR = BASE_DIR / 'data_download'
FEISHU_CONFIG_PATH = BASE_DIR / 'feishu_config.json'

DATA_DOWNLOAD_DIR.mkdir(exist_ok=True)

def load_json(path: Path) -> dict | list:
    """通用 JSON 读取器"""
    if not path.exists():
        return [] if 'token_config' in str(path) else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return [] if 'token_config' in str(path) else {}

def save_json(path: Path, data: dict | list) -> None:
    """通用 JSON 写入器"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_app_config() -> dict:
    """加载 小红书 APP_ID 和 SECRET"""
    config = load_json(APP_CONFIG_PATH)
    if not config or 'APP_ID' not in config:
        # 为了让报错更友好，打印出程序正在找的路径
        raise FileNotFoundError(f"❌ 无法加载 app_config.json，程序正在查找路径: {APP_CONFIG_PATH}")
    return config

def load_feishu_config() -> dict:
    """加载飞书配置"""
    config = load_json(FEISHU_CONFIG_PATH)
    required_keys = ['app_id', 'app_secret']
    if not config or any(k not in config for k in required_keys):
        return {}
    return config