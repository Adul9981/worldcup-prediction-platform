# 规则检查：发布版今日推荐数据

检查时间：2026-06-11

## 本次建设

- 新增公开数据文件 `data/templates/manual_recommendations.json`。
- 今日页优先读取后台本地保存；若本地没有策略，则读取公开发布文件。
- 后台新增“下载发布文件”按钮，可导出 `manual_recommendations.json`。
- 新增脚本 `tools/site/publish_manual_recommendations.py`，用于校验并发布后台导出的 JSON。
- 发布包已包含 `manual_recommendations.json`。

## 发布流程

1. 在 `/site/admin.html` 填写策略。
2. 点击“下载发布文件”。
3. 使用 `python3 tools/site/publish_manual_recommendations.py path/to/manual_recommendations.json` 写入数据目录。
4. 运行 `python3 tools/site/build_release.py` 重新生成发布包。

## 验证结果

- `node --check site/admin.js` 通过。
- `node --check site/today.js` 通过。
- `python3 -m py_compile tools/site/publish_manual_recommendations.py` 通过。
- 临时样例验证：今日页可以从公开 JSON 文件读取并置顶展示完整策略稿。
- 验证后已恢复空模板，避免测试内容进入发布包。
