import requests
import datetime
from src.auth.token_service import TokenManager, LoginRequiredError
from src.share.exporter import save_report
from src.utils.decorators import interactive_retry
from src.share.feishu_sync import feishu_client


def get_date_range():
    """日期选择逻辑"""
    print("\n1. 近7天  2. 近14天  3. 自定义")
    choice = input("请选择: ").strip()
    today = datetime.date.today()

    if choice == '1':
        end = today - datetime.timedelta(days=1)
        start = today - datetime.timedelta(days=7)
    elif choice == '2':
        end = today - datetime.timedelta(days=1)
        start = today - datetime.timedelta(days=14)
    else:
        s = input("开始日期 (yyyymmdd): ")
        e = input("结束日期 (yyyymmdd): ")
        if len(s) == 8: s = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        if len(e) == 8: e = f"{e[:4]}-{e[4:6]}-{e[6:]}"

        try:
            start = datetime.datetime.strptime(s, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(e, "%Y-%m-%d").date()
        except ValueError:
            print("❌ 日期格式错误，默认查询昨天")
            start = end = today - datetime.timedelta(days=1)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


@interactive_retry
def run_query_flow(advertiser_id, advertiser_name):
    """业务主流程"""
    try:
        token = TokenManager.get_valid_token(advertiser_id)
    except LoginRequiredError as e:
        print(f"❌ {e}")
        return

    start_date, end_date = get_date_range()

    url = "https://adapi.xiaohongshu.com/api/open/jg/data/report/offline/account"
    payload = {
        "advertiser_id": advertiser_id,
        "start_date": start_date,
        "end_date": end_date,
        "time_unit": "SUMMARY",
        "sort_column": "fee",
        "sort": "desc",
        "page_num": 1,
        "page_size": 1
    }

    print("\n⏳ 正在从聚光平台获取数据...")
    resp = requests.post(url, json=payload, headers={"Access-Token": token})
    res_json = resp.json()

    if res_json.get('code') != 0:
        raise Exception(f"API请求失败: {res_json.get('msg')}")

    if not res_json.get('data') or not res_json['data'].get('data_list'):
        print(f"⚠️ 账户 [{advertiser_name}] 在 {start_date} 至 {end_date} 期间无数据")
        return

    data = res_json['data']['data_list'][0]

    # [关键修改] 将元数据写入 JSON，确保历史记录能读取到精确的原始信息
    metrics = {
        "账户ID": str(advertiser_id),
        "账户名称": advertiser_name,  # [新增] 保存原始名称，防止文件名转义导致去重失败
        "开始日期": start_date,  # [新增] 保存标准日期格式
        "结束日期": end_date,  # [新增]

        "消费": data.get("fee", 0),
        "展现量": data.get("impression", 0),
        "点击量": data.get("click", 0),
        "点击率": data.get("ctr", 0),
        "平均点击成本": data.get("acp", 0),
        "平均千次展现费用": data.get("cpm", 0),
        "互动量": data.get("interaction", 0),
        "私信进线数": data.get("message_consult", 0),
        "私信进线成本": data.get("message_consult_cpl", 0),
        "私信开口数": data.get("initiative_message", 0),
        "私信开口条数": data.get("message", 0),
        "私信开口成本": data.get("initiative_message_cpl", 0),
        "私信留资数": data.get("msg_leads_num", 0),
        "私信留资成本": data.get("msg_leads_cost", 0),
        "平均响应时长(分)": data.get("message_fst_reply_time_avg", 0)
    }

    print("\n" + "=" * 50)
    print(f"📊 {advertiser_name}")
    print(f"📅 周期: {start_date} ~ {end_date}")
    print("-" * 50)
    # 打印时跳过元数据字段，只显示指标
    meta_keys = ["账户ID", "账户名称", "开始日期", "结束日期"]
    for k, v in metrics.items():
        if k not in meta_keys:
            print(f"{k:<15}: {v}")
    print("=" * 50)

    save_report(metrics, advertiser_name, start_date, end_date)

    print("\n🚀 [下一步操作]")
    sync_feishu = input("是否将此数据同步到飞书多维表格? (y/n): ").strip().lower()

    if sync_feishu == 'y':
        feishu_client.sync_to_feishu(metrics, str(advertiser_id), advertiser_name, start_date, end_date)
    else:
        print("已跳过飞书同步。")