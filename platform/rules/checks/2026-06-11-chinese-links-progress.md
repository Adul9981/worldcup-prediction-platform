# Rule Check: Chinese Display, Invite Links, Progress Overview

## User Requirements

1. Polymarket links must include `?via=serene77mc-g6kj`.
2. Build a Chinese-English glossary and replace English country/team/player/term display with Chinese.
3. Build a World Cup progress overview page.
4. User-facing titles must always be Chinese.

## Rules Added

- R009 Polymarket 链接必须带邀请码.
- R010 用户可见标题永远中文.
- R011 必须维护中英文对照知识库.
- R012 必须有世界杯进度纵览.

## Files Added

- `knowledge/11_cn_en_glossary.md`
- `data/templates/glossary_cn_en.csv`
- `site/progress.html`
- `site/progress.js`

## Verification

- Workbench page title: Chinese.
- Progress page title: Chinese.
- First opportunity card title: Chinese.
- First ranking card title: Chinese.
- Ranking explanatory text: Chinese.
- Polymarket market-link count without invite code: 0.

## Remaining Notes

`Polymarket` remains as a platform brand name in link labels and source labels. All market titles, module titles and page titles are Chinese.
