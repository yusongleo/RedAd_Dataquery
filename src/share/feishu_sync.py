import requests
import json
import time
import datetime
from typing import Dict, Optional, List, Any
from src.utils.config import load_feishu_config, FEISHU_CONFIG_PATH, save_json


class FeishuSync:
    def __init__(self):
        self.main_config = load_feishu_config()
        self.tenant_access_token = None
        self.token_expire_time = 0

    def _get_token(self) -> str:
        """获取或刷新飞书 Tenant Access Token"""
        if not self.main_config:
            return ""

        now = time.time()
        # 提前 5 分钟刷新 Token
        if self.tenant_access_token and now < self.token_expire_time:
            return self.tenant_access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.main_config.get("app_id"),
            "app_secret": self.main_config.get("app_secret")
        }

        try:
            resp = requests.post(url, json=payload)
            data = resp.json()
            if data.get("code") == 0:
                self.tenant_access_token = data.get("tenant_access_token")
                self.token_expire_time = now + data.get("expire", 7200) - 300
                return self.tenant_access_token
            else:
                print(f"❌ 飞书鉴权失败: {data.get('msg')}")
                return ""
        except Exception as e:
            print(f"❌ 连接飞书失败: {e}")
            return ""

    def _clean_number(self, value: Any) -> float:
        """数据清洗：将各种格式的数值统一转换为 float"""
        if value is None: return 0.0
        if isinstance(value, (int, float)): return float(value)
        if isinstance(value, str):
            s = value.strip().replace(',', '')
            if '%' in s:
                try:
                    return float(s.replace('%', '')) / 100.0
                except:
                    return 0.0
            if s in ['-', 'N/A', 'nan', 'null', '']: return 0.0
            try:
                return float(s)
            except:
                return 0.0
        return 0.0

    def _date_to_timestamp(self, date_str: str) -> int:
        """日期标准化：统一转换为毫秒级时间戳"""
        try:
            date_s = str(date_str).strip()
            if date_s.isdigit() and len(date_s) >= 13: return int(date_s)
            if date_s.isdigit() and len(date_s) == 10: return int(date_s) * 1000

            dt = None
            if '-' in date_s:
                if ':' in date_s:
                    dt = datetime.datetime.strptime(date_s[:19], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.datetime.strptime(date_s, "%Y-%m-%d")
            else:
                dt = datetime.datetime.strptime(date_s, "%Y%m%d")
            return int(dt.timestamp() * 1000)
        except Exception:
            return int(time.time() * 1000)

    def _find_existing_table_id(self, app_token: str, advertiser_name: str, advertiser_id: str) -> Optional[str]:
        """
        [云端发现升级]
        优先查找: 账户名_账户ID (精准匹配)
        兜底查找: 账户名_ (前缀匹配，兼容旧版)
        """
        try:
            token = self._get_token()
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
            headers = {"Authorization": f"Bearer {token}"}

            params = {"page_size": 100}
            resp = requests.get(url, headers=headers, params=params)
            res = resp.json()

            if res.get("code") != 0:
                return None

            clean_name = "".join(c for c in advertiser_name if c.isalnum())
            target_exact_name = f"{clean_name}_{advertiser_id}"  # 目标精准名称

            items = res.get("data", {}).get("items", [])

            # 1. 优先：寻找 "Name_ID" 格式的完美匹配
            for item in items:
                if item.get("name") == target_exact_name:
                    print(f"🔍 [智能关联] 发现精准匹配表格: {target_exact_name}")
                    return item.get("table_id")

            # 2. 兜底：寻找 "Name_Timestamp" 等旧格式
            for item in items:
                t_name = item.get("name", "")
                if t_name.startswith(clean_name + "_"):
                    print(f"🔍 [智能关联] 发现历史兼容表格: {t_name}")
                    return item.get("table_id")

            return None

        except Exception as e:
            print(f"⚠️ 云端查找表格失败: {e}")
            return None

    def _create_table_and_update_config(self, app_token: str, advertiser_id: str, advertiser_name: str) -> Optional[
        str]:
        """创建新表"""

        # 1. 先去云端找找看有没有现成的 (传入 ID 以便精准查找)
        existing_table_id = self._find_existing_table_id(app_token, advertiser_name, advertiser_id)
        if existing_table_id:
            self._update_local_config(advertiser_id, advertiser_name, existing_table_id)
            return existing_table_id

        # 2. 新建表格逻辑
        token = self._get_token()
        if not token: return None

        clean_name = "".join(c for c in advertiser_name if c.isalnum())

        # 表格命名规则：清洗后的名称 + "_" + 账户ID
        # 示例：南椿序写真馆_1767494969
        table_name = f"{clean_name}_{advertiser_id}"

        # 飞书表名有长度限制，如果太长则从前面截断名称，保留后面的ID
        if len(table_name) > 90:
            table_name = f"{clean_name[:50]}_{advertiser_id}"

        print(f"🔨 正在创建新表: {table_name} ...")

        fields_payload = [
            {"field_name": "账户名称", "type": 1},
            {"field_name": "开始日期", "type": 5},
            {"field_name": "结束日期", "type": 5},
            {"field_name": "消费", "type": 2},
            {"field_name": "展现量", "type": 2},
            {"field_name": "点击量", "type": 2},
            {"field_name": "点击率", "type": 2},
            {"field_name": "平均点击成本", "type": 2},
            {"field_name": "平均千次展现费用", "type": 2},
            {"field_name": "互动量", "type": 2},
            {"field_name": "私信进线数", "type": 2},
            {"field_name": "私信进线成本", "type": 2},
            {"field_name": "私信留资数", "type": 2},
            {"field_name": "私信留资成本", "type": 2},
            {"field_name": "私信开口数", "type": 2},
            {"field_name": "私信开口条数", "type": 2},
            {"field_name": "私信开口成本", "type": 2},
            {"field_name": "平均响应时长(分)", "type": 2}
        ]

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        payload = {
            "table": {
                "name": table_name,
                "default_view_name": "默认视图",
                "fields": fields_payload
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload)
            res_json = resp.json()

            if res_json.get("code") == 0:
                new_table_id = res_json["data"]["table_id"]
                print(f"✅ 新表创建成功! Table ID: {new_table_id}")
                self._update_local_config(advertiser_id, advertiser_name, new_table_id)
                return new_table_id
            else:
                print(f"❌ 建表失败: {res_json.get('msg')}")
                return None
        except Exception as e:
            print(f"❌ 建表异常: {e}")
            return None

    def _update_local_config(self, advertiser_id: str, advertiser_name: str, table_id: str):
        """更新本地配置文件"""
        try:
            current_config = load_feishu_config()
            if "account_mapping" not in current_config:
                current_config["account_mapping"] = {}
            current_config["account_mapping"][str(advertiser_id)] = {
                "name_remark": advertiser_name,
                "table_id": table_id
            }
            save_json(FEISHU_CONFIG_PATH, current_config)
            self.main_config = current_config
        except Exception as e:
            print(f"⚠️ 配置更新失败: {e}")

    def _check_duplicate(self, app_token: str, table_id: str, acc_name: str, start_ts: int, end_ts: int) -> bool:
        """幂等性检查"""
        try:
            token = self._get_token()
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"

            filter_str = f'CurrentValue.[账户名称] = "{acc_name}"'

            params = {
                "filter": filter_str,
                "page_size": 100
            }

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(url, headers=headers, params=params)
            res = resp.json()

            if res.get("code") == 0 and res.get("data") and res.get("data").get("items"):
                items = res["data"]["items"]
                for item in items:
                    fields = item.get("fields", {})
                    if fields.get("开始日期") == start_ts and fields.get("结束日期") == end_ts:
                        return True
            return False

        except Exception as e:
            return False

    def sync_to_feishu(self, metrics: Dict, advertiser_id: str, advertiser_name: str, start_date: str, end_date: str,
                       retry_count=0):
        """核心同步逻辑"""
        mapping = self.main_config.get("account_mapping", {})
        target = mapping.get(str(advertiser_id))
        default_app_token = self.main_config.get("default_app_token")

        target_conf = None

        # 1. 尝试使用本地配置
        if target and target.get("table_id") and retry_count == 0:
            target_conf = {"app_token": target.get("app_token") or default_app_token, "table_id": target["table_id"]}
        else:
            # 2. 本地无配置，尝试云端发现或新建
            if not default_app_token:
                print("❌ 缺少 default_app_token，无法处理")
                return

            # 传入 advertiser_id 供命名使用
            new_or_found_id = self._create_table_and_update_config(default_app_token, advertiser_id, advertiser_name)
            if new_or_found_id:
                target_conf = {"app_token": default_app_token, "table_id": new_or_found_id}
            else:
                return

        token = self._get_token()
        if not token: return

        ts_start = self._date_to_timestamp(start_date)
        ts_end = self._date_to_timestamp(end_date)

        # 3. 查重
        if retry_count == 0:
            print(f"🔍 正在检查 [{advertiser_name}] 的历史记录...")
            is_dup = self._check_duplicate(target_conf['app_token'], target_conf['table_id'], advertiser_name, ts_start,
                                           ts_end)
            if is_dup:
                print(f"⚠️ [重复拦截] 该账户在 {start_date} 至 {end_date} 的数据已存在于飞书。")
                print("⏭️ 已自动跳过同步，无需重复操作。")
                return

        # 4. 写入
        record_fields = {
            "账户名称": advertiser_name,
            "开始日期": ts_start,
            "结束日期": ts_end
        }
        number_keys = [
            "消费", "展现量", "点击量", "点击率", "平均点击成本", "平均千次展现费用",
            "互动量", "私信进线数", "私信进线成本", "私信留资数", "私信留资成本",
            "私信开口数", "私信开口条数", "私信开口成本", "平均响应时长(分)"
        ]
        for key in number_keys:
            record_fields[key] = self._clean_number(metrics.get(key, 0))

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{target_conf['app_token']}/tables/{target_conf['table_id']}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"fields": record_fields}

        try:
            resp = requests.post(url, headers=headers, json=payload)
            res_json = resp.json()

            if res_json.get("code") == 0:
                print("✅ 飞书同步成功！")
            else:
                msg = res_json.get('msg', '')
                print(f"❌ 写入失败: {msg}")

                # 5. 自动纠错
                error_triggers = ["TableIdNotFound", "FieldConvFail", "ConvFail", "Range Not Found", "FieldIdNotFound"]
                if any(x in msg for x in error_triggers):
                    if retry_count < 1:
                        print("♻️ 检测到配置过期或表格异常，正在自动创建新表并重试...")
                        self._update_local_config(advertiser_id, advertiser_name, "")
                        self.sync_to_feishu(metrics, advertiser_id, advertiser_name, start_date, end_date,
                                            retry_count=1)
                    else:
                        print("🔴 重试后依然失败，请检查飞书后台权限。")

        except Exception as e:
            print(f"❌ 网络异常: {e}")


feishu_client = FeishuSync()