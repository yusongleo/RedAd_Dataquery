import json
import datetime
import pyperclip
from src.utils.config import DATA_DOWNLOAD_DIR


def save_report(metrics: dict, name: str, start: str, end: str):
    """保存 JSON 并复制到剪贴板"""

    # 1. 准备文本内容
    text_content = f"⭐ {name} ⭐聚光数据\n🎉数据周期: {start} 至 {end}\n\n"
    text_content += "\n".join([f"{k}: {v}" for k, v in metrics.items()])

    # 2. 复制到剪贴板
    try:
        pyperclip.copy(text_content)
        print("\n📋 数据已复制到剪贴板！(可直接粘贴发送)")
    except Exception:
        pass

    # 3. 保存文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    # 清理文件名中的非法字符
    safe_name = "".join([c if c.isalnum() else "_" for c in name])
    filename = f"{safe_name}_{start.replace('-', '')}_{end.replace('-', '')}_{timestamp}.json"

    path = DATA_DOWNLOAD_DIR / filename

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=4)

    # [修改点] 使用 path.resolve() 显示绝对路径
    print(f"💾 文件已保存至: {path.resolve()}")