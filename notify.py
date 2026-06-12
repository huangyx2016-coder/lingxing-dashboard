"""Send dashboard link to 邓子平 & Mark via Feishu."""
import json, requests
from datetime import datetime

APP_ID = "cli_aaaa6fd809795cd9"
APP_SECRET = "4nG5h1Fx0xHsHhlcvmgIfbSinpZYUIFd"
RECIPIENTS = [
    ("邓子平", "ou_744c1351a6b58ac8b8e259184cd1dbc8"),
    ("Mark", "ou_44d1d3cbeb2e1829ddb5fa28351ecd89"),
]
URL = "https://huangyx2016-coder.github.io/lingxing-dashboard/"


def main():
    with open("lingxing_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

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

    for name, open_id in RECIPIENTS:
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
