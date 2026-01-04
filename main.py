import sys
import datetime
from src.utils.config import load_app_config
from src.auth.token_service import TokenManager
from src.auth.oauth import new_authorization
from src.data_query.data_query import run_query_flow
# [新增] 导入历史记录模块
from src.data_query.history import view_history_flow

def format_ts(ts: int) -> str:
    """将时间戳转换为可读字符串"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def view_accounts_detail():
    """详细展示所有账户的授权状态（含过期时间）"""
    tokens = TokenManager.get_tokens()
    if not tokens:
        print("\n⚠️ 暂无已授权的聚光账户")
        return

    print("\n" + "="*100)
    print(f"{'序号':<5} {'账户名称':<25} {'账户ID':<15} {'Access过期时间':<20} {'Refresh过期时间'}")
    print("-" * 100)
    
    for idx, t in enumerate(tokens, 1):
        acc_expire = format_ts(t.get('access_expires_at', 0))
        ref_expire = format_ts(t.get('refresh_expires_at', 0))
        print(f"{idx:<5} {t['advertiser_name']:<25} {t['advertiser_id']:<15} {acc_expire:<20} {ref_expire}")
    print("="*100)
    input("\n按回车键返回主菜单...")

def select_account():
    """简略展示账户供选择"""
    tokens = TokenManager.get_tokens()
    if not tokens:
        print("⚠️ 暂无授权账户，请先选择功能 2 进行添加。")
        return None
    
    print("\n请选择要查询的账户：")
    print("-" * 40)
    for i, t in enumerate(tokens, 1):
        print(f"{i}. {t['advertiser_name']} (ID: {t['advertiser_id']})")
    print("-" * 40)
    
    choice = input("请输入序号 (0 返回): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return None
    
    idx = int(choice) - 1
    if 0 <= idx < len(tokens):
        return tokens[idx]
    return None

def main():
    try:
        load_app_config()
    except Exception as e:
        print(e)
        input("按回车退出...")
        sys.exit(1)

    while True:
        print("\n" + "="*40)
        print(" RedAd DataQuery v2.2 (Token托管版)")
        print("="*40)
        print("1. 数据查询 (自动刷新Token)")
        print("2. 新增/重新授权账户")
        print("3. 查看已授权账户状态")
        print("4. 查询历史记录 (打开/导出)") # [新增选项]
        print("q. 退出程序")
        
        cmd = input("请输入指令: ").strip().lower()
        
        if cmd == '1':
            account = select_account()
            if account:
                run_query_flow(account['advertiser_id'], account['advertiser_name'])
        
        elif cmd == '2':
            new_authorization()

        elif cmd == '3':
            view_accounts_detail()

        elif cmd == '4':
            # [新增调用]
            view_history_flow()
            
        elif cmd == 'q':
            print("感谢使用，再见！")
            break
        else:
            print("❌ 无效指令，请重新输入")

if __name__ == "__main__":
    main()