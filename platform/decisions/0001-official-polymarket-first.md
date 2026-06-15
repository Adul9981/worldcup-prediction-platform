# ADR-0001：优先使用官方 Polymarket Agent Skills

日期：2026-06-10。

## 决策

世界杯预测市场交易工具平台优先使用官方 `Polymarket/agent-skills` 作为 Polymarket 接入参考。

本地路径：

- `/Users/ad/Documents/2026世界杯/integrations/agent-skills`

## 原因

- 官方维护。
- 面向 AI agents。
- 覆盖市场数据、认证、订单、WebSocket、仓位、桥接、gasless 等完整知识。
- 当前阶段只需要其中的只读市场数据能力。

## 替代方案

- 社区 skills 仓库。
- 官方 SDK 直接接入。
- 自己手写所有接口。

## 结果

- 社区仓库保留为备选参考。
- 官方 SDK `py-clob-client` 保留为 Python 参考。
- 第一阶段不启用交易能力。
