"""领星 ERP OpenAPI 客户端

注意：领星服务器会做 TLS 指纹检测，Python requests/urllib 会被 403 拦截，
只有 curl（Windows schannel）能通过。因此 HTTP 层统一用 subprocess 调 curl。
"""
import json
import subprocess
import time
import copy
from typing import Optional
from urllib.parse import urlencode

from .sign import generate_sign

BASE_URL = "https://openapi.lingxing.com"


class LingxingClient:
    """领星 ERP API 客户端"""

    def __init__(self, app_id: str, app_secret: str, host: str = BASE_URL):
        self.app_id = app_id
        self.app_secret = app_secret
        self.host = host

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_at: float = 0

    # ── token 管理 ──────────────────────────────────────

    def ensure_token(self) -> str:
        if self.access_token and time.time() < self.expires_at - 120:
            return self.access_token
        if self.refresh_token:
            try:
                self._do_refresh()
                return self.access_token
            except Exception:
                pass
        self._do_get_token()
        return self.access_token

    def _do_get_token(self):
        result = _curl(
            "POST",
            f"{self.host}/api/auth-server/oauth/access-token",
            form={"appId": self.app_id, "appSecret": self.app_secret},
        )
        self._save_token(result.get("data", {}))

    def _do_refresh(self):
        result = _curl(
            "POST",
            f"{self.host}/api/auth-server/oauth/refresh",
            form={"appId": self.app_id, "refreshToken": self.refresh_token},
        )
        self._save_token(result.get("data", {}))

    def _save_token(self, data: dict):
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = time.time() + data.get("expires_in", 7200)

    # ── API 请求 ────────────────────────────────────────

    def get(self, path: str, **params) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[dict] = None, **params) -> dict:
        return self._request("POST", path, params=params, body=body)

    def _request(self, method: str, path: str,
                 params: Optional[dict] = None,
                 body: Optional[dict] = None) -> dict:
        token = self.ensure_token()
        params = dict(params or {})
        ts = str(int(time.time()))

        # 组装签名参数
        sign_params = copy.deepcopy(body) if body else {}
        sign_params.update(params)
        sign_params.update({
            "app_key": self.app_id,
            "access_token": token,
            "timestamp": ts,
        })

        # 生成签名
        sign = generate_sign(self.app_id, sign_params)

        # 构建 query string
        query = {
            "access_token": token,
            "app_key": self.app_id,
            "timestamp": ts,
            "sign": sign,
        }
        query.update(params)

        if body:
            return _curl(method, self.host + path, query=query, json_body=body)
        else:
            return _curl(method, self.host + path, query=query)


class LingxingAPIError(Exception):
    def __init__(self, code, message, raw):
        self.code = code
        self.message = message
        self.raw = raw
        super().__init__(f"[{code}] {message}")


# ── curl 调用 ──────────────────────────────────────────

def _curl(method: str, url: str,
          query: Optional[dict] = None,
          form: Optional[dict] = None,
          json_body: Optional[dict] = None,
          timeout: int = 60) -> dict:
    """通过 curl 发 HTTP 请求，返回解析后的 JSON dict"""
    cmd = ["curl", "-s", "-X", method, "--max-time", str(timeout)]

    if query:
        url = url + "?" + urlencode(query)

    cmd.append(url)

    if form:
        for k, v in form.items():
            cmd.extend(["-F", f"{k}={v}"])
    elif json_body:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["-d", json.dumps(json_body, ensure_ascii=False)])

    proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", text=True, timeout=timeout + 5)

    if proc.returncode != 0:
        raise LingxingAPIError(-1, f"curl failed: {proc.stderr.strip()}", {})

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise LingxingAPIError(-2, f"Invalid JSON: {proc.stdout[:200]}", {})

    code = result.get("code")
    if code not in (200, "200", 0, "0"):
        msg = result.get("msg") or result.get("message") or ""
        raise LingxingAPIError(code, msg, result)

    return result
