# 本机部署指南（TradingView → Schwab 下单桥）

服务跑在你自己电脑上，TradingView 通过 cloudflare 隧道访问它。

## 1. 装 cloudflared（一次性）

- 打开 https://github.com/cloudflare/cloudflared/releases ，下载 `cloudflared-windows-amd64.exe`
- 改名为 `cloudflared.exe`，放到本目录（和 `app.py` 同一级）

## 2. 启动服务

双击 `start_bridge.bat`（Mac/Linux 用 `bash start_bridge.sh`）。
它会读取 `.env` 并在 `http://127.0.0.1:8000` 启动服务。

## 3. 暴露公网地址

再开一个终端，进本目录跑：

```
cloudflared.exe tunnel --url http://localhost:8000
```

会给你一个 `https://xxx.trycloudflare.com` 地址——这就是填到 TradingView
alert 里 **Webhook URL** 后面的部分：`https://xxx.trycloudflare.com/webhook`。

注意：
- **quick tunnel 的地址每次重启都会变**，变了就要去 TradingView 更新 webhook URL。
  想固定地址就注册个免费 Cloudflare 账号建 named tunnel（dashboard 里点几下就行），
  之后地址永久有效。
- 电脑和 cloudflared 在美股时段（北京时间 21:30–04:30）必须一直开着。

## 4. 防休眠 + VPN（重要）

- Windows 设置 → 系统 → 电源 → 睡眠设为"从不"（至少覆盖美股时段）
- VPN 切到**美国节点**并保持连接：Schwab API 对 IP 地域敏感，国内/德国 IP 可能被拒
- 建议 VPN 设开机自启

## 5. 每周维护（1 分钟）

Schwab 的 refresh token 每 7 天过期。每周跑一次：

```
.venv\Scripts\python auth.py
```

浏览器登录 Schwab 点 Allow 即可。忘了续的话服务会返回 502，日志里有明确提示。

## 6. TradingView 侧配置

1. 在图表上建 alert，勾选 **Webhook URL**，填 `https://你的隧道地址/webhook`
2. Message 文本框粘贴 `alert_template.json` 的内容（删掉 `_` 开头的说明行），
   把 `secret` 换成你 `.env` 里的 `WEBHOOK_SECRET`，`{{ticker}}` 会自动替换成标的代码
3. 先 `DRY_RUN=true` 跑几天，看 `logs/trades.log` 确认信号→订单解析都对，再改 `false` 开真单
