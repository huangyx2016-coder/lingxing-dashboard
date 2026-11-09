"""Send daily dashboard summary (text + per-store screenshots) via Feishu."""
import json
import os
import secrets
import sys
import time
from datetime import datetime

import requests

sys.path.insert(0, "/root/review-app")
import dash_category  # noqa: E402

def _load_env(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".feishu.env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except FileNotFoundError:
        pass


_load_env()
APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
DZP = ("邓子平", "REDACTED_OPEN_ID")
MARK = ("Mark", "REDACTED_OPEN_ID")
URL = "https://dashboard.jewelaurea.com/"
SHOT_TOKEN_FILE = "/root/review-app/.shot_token"
def shot_specs(data):
    orders = data.get("orders") or {}
    counts = {"e": 0, "n": 0, "o": 0}
    for name in orders:
        c = dash_category.combined(name)
        if c == "耳环":
            counts["e"] += 1
        elif c == "项链+手链":
            counts["n"] += 1
        else:
            counts["o"] += 1
    specs = [("summary", "view=summary")]
    for code in ("e", "n", "o"):
        for i, off in enumerate(range(0, counts[code], 35), 1):
            specs.append(("%s%d" % (code, i),
                          "cat=%s&offset=%d&limit=35" % (code, off)))
    return specs


def verify_local_data(expected_orders: int) -> bool:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "index.html")
    if os.path.exists(html_path):
        print(f"  Local HTML: {os.path.getsize(html_path):,} bytes OK")
        return True
    print("  Local HTML not found")
    return False


def build_text(data):
    days = (data.get("dates") or [])[-2:]
    orders = data.get("orders") or {}

    def cat(name):
        c = dash_category.combined(name)
        if c == "耳环":
            return "e"
        if c == "项链+手链":
            return "n"
        return "o"

    def total(code):
        o = a = 0
        for k, v in orders.items():
            if code != "all" and cat(k) != code:
                continue
            o += sum(int(v["daily"].get(x) or 0) for x in days)
            a += sum(float(v["amount"].get(x) or 0) for x in days)
        return o, a

    e, n, allx = total("e"), total("n"), total("all")
    rng = (days[0] + "–" + days[-1]) if len(days) > 1 else (days[0] if days else "")
    now = datetime.now().strftime("%m-%d %H:%M")
    return (
        "每日订单自动可视化 - 数据已更新 (%s)\n"
        "近2天（%s，订单数 / 销售额）\n"
        "耳环：%s 单，销售额 $%s\n"
        "项链+手链：%s 单，销售额 $%s\n"
        "全部店铺：%s 单，销售额 $%s\n"
        "各店铺明细见下方截图\n"
        "完整看板：%s"
    ) % (now, rng,
         format(e[0], ","), format(e[1], ",.2f"),
         format(n[0], ","), format(n[1], ",.2f"),
         format(allx[0], ","), format(allx[1], ",.2f"), URL)


def make_shots(specs):
    """Render the summary and store-detail pages with headless Chromium."""
    token = secrets.token_hex(24)
    with open(SHOT_TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    os.chmod(SHOT_TOKEN_FILE, 0o600)
    paths = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1400, "height": 1000})
            for name, query in specs:
                url = ("http://127.0.0.1:8080/dashboard/shot?token=%s&%s"
                       % (token, query))
                page.goto(url, wait_until="networkidle", timeout=60000)
                path = "/tmp/preview_%s.png" % name
                page.screenshot(path=path, full_page=True)
                paths.append(path)
            browser.close()
    finally:
        try:
            os.remove(SHOT_TOKEN_FILE)
        except OSError:
            pass
    return paths


def main():
    dry = "--dry-run" in sys.argv
    scheduled = "--scheduled" in sys.argv

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "lingxing_data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Verifying deployment...")
    if not verify_local_data(data.get("total_orders", 0)):
        print("FAILED: local HTML not generated")
        return

    text = build_text(data)
    print(text)

    shots = []
    try:
        shots = make_shots(shot_specs(data))
        print("screenshots: %d" % len(shots))
    except Exception as e:
        print("screenshot failed: %s" % e)

    if dry:
        print("dry run, not sending")
        for p in shots:
            print(p, os.path.getsize(p))
        return

    token = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=30
    ).json()["tenant_access_token"]
    H = {"Authorization": "Bearer " + token}

    image_keys = []
    for path in shots:
        with open(path, "rb") as f:
            up = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/images", headers=H,
                data={"image_type": "message"},
                files={"image": (os.path.basename(path), f, "image/png")},
                timeout=60).json()
        key = (up.get("data") or {}).get("image_key")
        if key:
            image_keys.append(key)
        else:
            print("upload failed:", path, str(up)[:160])

    recipients = [DZP]
    if scheduled:
        recipients.append(MARK)
    if "--to-mark" in sys.argv:
        recipients = [MARK]
    if "--to-both" in sys.argv:
        recipients = [DZP, MARK]

    for name, open_id in recipients:
        ok = bool(image_keys)
        for key in image_keys:
            r = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
                headers={**H, "Content-Type": "application/json"},
                json={"receive_id": open_id, "msg_type": "image",
                      "content": json.dumps({"image_key": key})},
                timeout=30).json()
            ok = ok and r.get("code") == 0
            time.sleep(0.3)
        print(f"{name}: {'OK' if ok else 'Failed'} ({len(image_keys)} images)")

    for p in shots:
        try:
            os.remove(p)
        except OSError:
            pass


if __name__ == "__main__":
    main()
