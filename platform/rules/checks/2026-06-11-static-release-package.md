# 规则检查：静态发布包

检查时间：2026-06-11

## 本次建设

- 新增 `tools/site/build_release.py`。
- 生成发布目录 `dist/worldcup-prediction-platform`。
- 发布包包含 `/site/` 页面和 `/data/` 数据。
- 发布包可作为静态站点根目录部署。

## 发布包验证

- 首页：加载成功，预测选题 61。
- 市场页：加载成功，当前显示 61 个选题。
- 进度页：加载成功，赛程 104 场，预测选题 61。
- 三个页面均未出现数据加载失败。
- 三个页面均未出现仓位、下注金额、下注单位。
- 市场外链邀请码缺失数为 0。

## 当前发布入口

- `dist/worldcup-prediction-platform/site/index.html`
- `dist/worldcup-prediction-platform/site/markets.html`
- `dist/worldcup-prediction-platform/site/progress.html`
