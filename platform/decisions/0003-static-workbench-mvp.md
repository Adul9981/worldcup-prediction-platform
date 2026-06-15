# 0003 Static Workbench MVP

## Decision

第一版网站采用静态 HTML/CSS/JavaScript，不引入前端框架和构建链。

## Reason

当前目标是尽快验证功能是否正常，而不是先做订阅、登录、部署和复杂前端工程。

静态工作台可以直接读取现有 CSV 输出，最快验证：

- 三榜是否有用。
- 仓位显示是否清晰。
- 联盟链接是否正确。
- 只读风险边界是否明确。

## Scope

包含：

- 今日三榜。
- 市场统计。
- 仓位纪律。
- 状态分布。
- 筛选和搜索。
- Polymarket 跳转链接。

不包含：

- 账号系统。
- 付费墙。
- 钱包。
- 下单。
- 服务端 API。

## Run

```bash
python3 -m http.server 4173
```

```text
http://127.0.0.1:4173/site/index.html
```
