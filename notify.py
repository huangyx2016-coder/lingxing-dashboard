"""Send dashboard link to 邓子平 (& Mark only on scheduled runs) via Feishu."""
import json, os, requests, sys, time
from datetime import datetime

APP_ID = "cli_aaaa6fd809795cd9"
APP_SECRET = "4nG5h1Fx0xHsHhlcvmgIfbSinpZYUIFd"
DZP = ("邓子平", "ou_744c1351a6b58ac8b8e259184cd1dbc8")
MARK = ("Mark", "ou_44d1d3cbeb2e1829ddb5fa28351ecd89")
URL = "http://39.103.204.178/"


def verify_local_data(expected_orders: int) -> bool:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "index.html")
    if os.path.exists(html_path):
        print(f"  Local HTML: {os.path.getsize(html_path):,} bytes OK")
        return True
    print("  Local HTML not found")
    return False


def main():
    scheduled = "--scheduled" in sys.argv

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "lingxing_data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Verifying deployment...")
    if not verify_local_data(data.get("total_orders", 0)):
        print("FAILED: local HTML not generated")
        return

    now = datetime.now().strftime("%m-%d %H:%M")
    text = (
        f"每日订单自动可视化 - 数据已更新 ({now})\n"
        f"近7天总订单: {data.get('total_orders', 0):,} 单\n"
        f"近7天总金额: ${data.get('total_amount', 0):,.0f}\n"
        f"店铺数: {data.get('shops_count', 0)}\n"
        f"FBA可售: {data['stock_summary']['available']:,}\n"
        f"\n查看详情: {URL}"
    )

    token = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=30
    ).json()["tenant_access_token"]

    # 邓子平 always receives; Mark only on scheduled runs
    recipients = [DZP]
    if scheduled:
        recipients.append(MARK)

    for name, open_id in recipients:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "receive_id": open_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
            timeout=30,
        ).json()

        if resp.get("code") == 0:
            print(f"{name}: OK")
        else:
            print(f"{name}: Failed - {resp}")


if __name__ == "__main__":
    main()
