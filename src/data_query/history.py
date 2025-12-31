import os
import json
import tempfile
import pyperclip
import platform
import subprocess
from pathlib import Path
from src.utils.config import DATA_DOWNLOAD_DIR
from src.share.feishu_sync import feishu_client


def parse_filename(filename: str):
    """解析文件名 (仅作为兼容旧文件的备选方案)"""
    try:
        stem = Path(filename).stem
        parts = stem.split('_')
        if len(parts) >= 5:
            query_time = f"{parts[-2]} {parts[-1].replace('.', ':')}"
            end_date = parts[-3]
            start_date = parts[-4]
            account_name = "_".join(parts[:-4])
            return {
                "name": account_name,
                "range": f"{start_date} -> {end_date}",
                "time": query_time,
                "file": filename
            }
    except Exception:
        pass
    return None


def load_and_format_content(file_path: Path) -> str:
    """读取JSON并格式化为易读文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        text = ""
        for k, v in data.items():
            text += f"{k}: {v}\n"
        return text
    except Exception as e:
        return f"无法读取文件内容: {e}"


def open_as_txt(file_path: Path):
    content = load_and_format_content(file_path)
    temp_dir = tempfile.gettempdir()
    target_filename = file_path.stem + ".txt"
    temp_path = os.path.join(temp_dir, target_filename)

    try:
        with open(temp_path, 'w', encoding='utf-8') as tmp:
            tmp.write(content)
        print(f"📄 正在以文本模式打开: {target_filename} ...")

        if platform.system() == 'Windows':
            os.startfile(temp_path)
        elif platform.system() == 'Darwin':
            subprocess.call(('open', temp_path))
        else:
            subprocess.call(('xdg-open', temp_path))
    except Exception as e:
        print(f"❌ 打开文件失败: {e}")


def view_history_flow():
    files = sorted(DATA_DOWNLOAD_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)

    if not files:
        print("\n📂 data_download 目录为空，暂无查询记录。")
        return

    print("\n" + "=" * 90)
    print(f"{'序号':<5} {'账户名称':<25} {'数据周期':<25} {'查询时间 (YYYYMMDD HHMM)'}")
    print("-" * 90)

    valid_files = []

    for f in files:
        info = parse_filename(f.name)
        if info:
            valid_files.append(f)
            idx = len(valid_files)
            print(f"{idx:<5} {info['name']:<25} {info['range']:<25} {info['time']}")

    if not valid_files:
        print("没有符合命名规范的历史文件。")
        return

    print("=" * 90)

    choice = input("\n请输入文件序号进行操作 (0 返回): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return

    idx = int(choice) - 1
    if not (0 <= idx < len(valid_files)):
        print("❌ 无效序号")
        return

    target_file = valid_files[idx]

    while True:
        print(f"\n已选中: {target_file.name}")
        print("1. 复制内容到剪贴板")
        print("2. 打开文件 (文本模式)")
        print("3. 导出到飞书")
        print("0. 返回上一级")

        action = input("请选择操作: ").strip()

        if action == '1':
            content = load_and_format_content(target_file)
            pyperclip.copy(content)
            print("✅ 内容已复制到剪贴板！")

        elif action == '2':
            open_as_txt(target_file)

        elif action == '3':
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                acc_id = data.get("账户ID")
                if not acc_id:
                    print("\n⚠️ 错误：该文件缺少【账户ID】，无法同步。请使用最新版程序重新查询数据。")
                    continue

                # [关键修改] 优先使用 JSON 内部存储的精准元数据
                # 只有当文件是旧版本生成（没这些字段）时，才回退到文件名解析
                if data.get("账户名称") and data.get("开始日期"):
                    acc_name = data.get("账户名称")
                    start_date = data.get("开始日期")
                    end_date = data.get("结束日期")
                    # print(f"DEBUG: 使用精准元数据同步 -> {acc_name}")
                else:
                    # 兼容旧文件逻辑
                    info = parse_filename(target_file.name)
                    dates = info['range'].split(' -> ')
                    start_date = dates[0]
                    end_date = dates[1]
                    acc_name = info['name']
                    print(f"⚠️ 警告: 正在使用文件名 [{acc_name}] 进行同步，可能因特殊字符导致去重失败。建议重新查询。")

                feishu_client.sync_to_feishu(data, str(acc_id), acc_name, start_date, end_date)

            except Exception as e:
                print(f"❌ 同步过程出错: {e}")

        elif action == '0':
            break
        else:
            print("❌ 无效输入")