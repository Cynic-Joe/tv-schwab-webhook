# TradingView → Schwab 自动下单桥

TradingView 的 alert webhook 打到这台服务, 服务经 Schwab Trader API 下单。
单向：TradingView 只发信号，看不到账户和持仓（和官方券商集成的主要区别）。

**部署方式二选一**：本机 + cloudflared 看 `LOCAL_DEPLOY.md`；云服务器看下面第 4 步的 Render 方案。

## 你要做的 4 步

### 1. 注册 Schwab developer app（5 分钟，只能你自己做）
1. 打开 https://developer.schwab.com ，用 Schwab 账号登录
2. 创建一个 app，类型选 Individual，Redirect URI 填 `https://127.0.0.1:8182`
3. 拿到 **App Key** 和 **Secret**，准备好

### 2. 装服务
```bash
cd tv-schwab-webhook
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # 然后填好 WEBHOOK_SECRET / SCHWAB_API_KEY / SCHWAB_APP_SECRET
```

### 3. 授权（首次 + 之后每周一次）
```bash
export $(cat .env | grep SCHWAB | xargs)
.venv/bin/python auth.py
```
浏览器打开 Schwab 登录页，登录并点 Allow。token 存到 `token.json`。
**Schwab 的 refresh token 7 天过期，每周重跑一次 `auth.py` 就行。**

### 4. 跑起来 + 公网地址
```bash
export $(cat .env | xargs)
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```
TradingView webhook 需要公网 HTTPS 地址，两种选法：
- **省事**：Render.com 免费套餐部署这个目录（Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`），环境变量在 Render 面板里填
- **自己电脑跑**：用 `cloudflared tunnel` 或 ngrok 把 8000 端口暴露出去

### 5. TradingView 里配 alert
1. alert 窗口勾选 **Webhook URL**，填 `https://你的域名/webhook`
2. Message 粘贴 `alert_template.json` 的内容（把 `_` 开头的说明行删掉）
3. 先用 `DRY_RUN=true` 跑：服务只记日志不下单，去 `logs/trades.log` 确认信号解析对了，再改 `false` 开真单

## 信号格式
```json
{"secret": "...", "symbol": "AAPL", "action": "buy", "quantity": 5}
{"secret": "...", "symbol": "TSLA", "action": "sell", "dollars": 500}
{"secret": "...", "symbol": "NVDA", "action": "close"}
```
- `action`: buy / sell / close（close 按当前持仓股数全平）
- `quantity`: 按股数；`dollars`: 按金额按市价折算股数（向下取整）
- 风控：`SYMBOL_ALLOWLIST` 白名单 + `MAX_DOLLARS_PER_ORDER` 单笔上限，超了直接拒绝

## 注意事项
- 全是**市价单**，盘前盘后 Schwab 市价单可能不被接受，alert 策略建议只在常规时段触发
- 每次触发都会记到 `logs/trades.log`，对账看这个
- token 每 7 天要续一次，忘了续服务会返回 502 并在日志里提示重跑 auth.py
