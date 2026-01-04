import time
import requests
from typing import Dict, Optional
from src.utils.config import TOKEN_CONFIG_PATH, load_json, save_json, load_app_config

class LoginRequiredError(Exception):
    """自定义异常：Refresh Token 也过期了，必须重新扫码"""
    pass

class TokenManager:
    @staticmethod
    def get_tokens() -> list:
        return load_json(TOKEN_CONFIG_PATH)

    @staticmethod
    def _save_tokens(tokens: list):
        save_json(TOKEN_CONFIG_PATH, tokens)

    @classmethod
    def get_valid_token(cls, advertiser_id: str) -> str:
        """
        核心方法：获取有效的 Access Token。
        如果 Access 过期但 Refresh 有效，自动刷新并保存。
        如果都过期，抛出 LoginRequiredError。
        """
        tokens = cls.get_tokens()
        account = next((t for t in tokens if str(t['advertiser_id']) == str(advertiser_id)), None)

        if not account:
            raise ValueError(f"未找到账户 ID: {advertiser_id}")

        now = time.time()
        # 缓冲 300 秒，提前刷新
        if now < account['access_expires_at'] - 300:
            return account['access_token']

        # Access Token 过期，检查 Refresh Token
        if now < account['refresh_expires_at'] - 300:
            print(f"🔄 账户 [{account['advertiser_name']}] Token 已过期，正在自动刷新...")
            return cls._perform_refresh(account)
        
        # 都过期了
        raise LoginRequiredError(f"账户 [{account['advertiser_name']}] 授权已完全失效，请重新授权。")

    @classmethod
    def _perform_refresh(cls, account: Dict) -> str:
        app_config = load_app_config()
        url = "https://adapi.xiaohongshu.com/api/open/oauth2/refresh_token"
        payload = {
            "app_id": app_config['APP_ID'],
            "secret": app_config['SECRET'],
            "refresh_token": account['refresh_token']
        }
        
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        data = resp.json()

        if data.get('code') != 0:
            raise Exception(f"刷新失败: {data.get('msg')}")

        # 更新内存中的数据
        new_data = data['data']
        current_time = time.time()
        
        account['access_token'] = new_data['access_token']
        account['refresh_token'] = new_data['refresh_token']
        account['access_expires_at'] = int(current_time + new_data['access_token_expires_in'])
        account['refresh_expires_at'] = int(current_time + new_data['refresh_token_expires_in'])

        # 更新文件
        all_tokens = cls.get_tokens()
        for i, t in enumerate(all_tokens):
            if str(t['advertiser_id']) == str(account['advertiser_id']):
                all_tokens[i] = account
                break
        cls._save_tokens(all_tokens)
        
        print("✅ Token 自动刷新成功！")
        return account['access_token']

    @classmethod
    def add_or_update_token(cls, new_account_data: Dict):
        """供 oauth.py 调用，用于保存新授权的账户"""
        tokens = cls.get_tokens()
        # 检查是否存在，存在则更新，不存在则追加
        for i, t in enumerate(tokens):
            if str(t['advertiser_id']) == str(new_account_data['advertiser_id']):
                tokens[i] = new_account_data
                cls._save_tokens(tokens)
                return
        tokens.append(new_account_data)
        cls._save_tokens(tokens)