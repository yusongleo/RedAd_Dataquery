import time
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs
from src.utils.config import load_app_config, BASE_DIR, load_json
from src.auth.token_service import TokenManager

def new_authorization():
    """执行全新的授权流程"""
    config = load_app_config()
    auth_url_path = BASE_DIR / 'auth_url.json'
    
    # 尝试读取 Auth URL
    try:
        auth_url = load_json(auth_url_path)['auth_url']
    except Exception:
        print("❌ 无法找到 auth_url.json")
        return

    print("正在打开授权页面...")
    webbrowser.open(auth_url)
    
    redirect_url = input("\n请粘贴跳转后的完整 URL (或输入 q 取消): ").strip()
    if redirect_url.lower() in ['q', 'cancel', 'exit']:
        return

    # 解析 Code
    parsed = urlparse(redirect_url)
    code = parse_qs(parsed.query).get('auth_code', [None])[0]
    if not code:
        print("❌ URL 无效，未找到 auth_code")
        return

    # 换取 Token
    url = "https://adapi.xiaohongshu.com/api/open/oauth2/access_token"
    payload = {
        "app_id": config['APP_ID'],
        "secret": config['SECRET'],
        "auth_code": code
    }
    
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    res_json = resp.json()
    
    if res_json.get('code') != 0:
        print(f"❌ 授权失败: {res_json.get('msg')}")
        return

    # 处理数据并保存
    data = res_json['data']
    now = time.time()
    
    for advertiser in data.get('approval_advertisers', []):
        account_data = {
            'advertiser_id': str(advertiser['advertiser_id']),
            'advertiser_name': advertiser['advertiser_name'],
            'access_token': data['access_token'],
            'refresh_token': data['refresh_token'],
            'access_expires_at': int(now + data['access_token_expires_in']),
            'refresh_expires_at': int(now + data['refresh_token_expires_in'])
        }
        TokenManager.add_or_update_token(account_data)
        print(f"✅ 账户 [{advertiser['advertiser_name']}] 授权保存成功！")