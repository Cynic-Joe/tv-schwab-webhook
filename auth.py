"""首次 / 每周一次的 Schwab OAuth 授权.

跑之前先填好环境变量 SCHWAB_API_KEY / SCHWAB_APP_SECRET
(来自 developer.schwab.com 注册的 app),
然后:  python auth.py
浏览器会打开 Schwab 登录页, 登录并 Allow, token 存到 token.json.
refresh token 7 天过期, 每周重跑一次即可.
"""
import os

API_KEY = os.environ.get("SCHWAB_API_KEY", "")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET", "")
CALLBACK_URL = "https://127.0.0.1:8182"
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")

if __name__ == "__main__":
    assert API_KEY and APP_SECRET, "先设置 SCHWAB_API_KEY / SCHWAB_APP_SECRET 环境变量"
    import schwab.auth
    schwab.auth.easy_client(API_KEY, APP_SECRET, CALLBACK_URL, TOKEN_PATH)
    print("授权成功, token 已保存到", TOKEN_PATH)
