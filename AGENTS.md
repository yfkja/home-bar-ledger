# AGENTS.md — 给 AI agent 的台账维护手册

你（agent）是本仓库的唯一"录入员"。人类只拍照/报品名，你负责把 `data/bar_data.json` 维护成合法状态。

## 数据契约

顶层 7 个键：`updated`(YYYY-MM-DD) / `note` / `items[]` / `recipes[]` / `mixers[]` / `base_drinks[]` / `shopping{}` / `storage_notes`。

**items**（每瓶一行）：
`name`（主品名，唯一键）/ `brand` / `type` / `cat`（枚举：烈酒·基酒｜利口酒·苦酒·威末｜果酒·低度｜白酒｜葡萄酒｜啤酒｜兑饮基底·软饮）/ `abv`（数字，软饮填 0）/ `size` / `qty` / `stock`（在架｜已喝完｜快见底）/ `loc` / `flavor` / `tags[]` / `note`（含 `YYYY-MM-DD 入库` 溯源）/ `exp`（可空）/ `photo`（可空 URL）

**recipes**（每条配方一行）：
`name` / `spirits[]`（**必须用 items 里存在的 name**）/ `need[]`（辅料，结尾标 `（在架）` 或 `（待购）`）/ `ratio` / `style` / `verdict`（专业点评一句话）/ `level`（必填：零门槛｜零酒精｜简单｜推荐｜进阶，可复合如"简单·经典"）

**mixers**：`name` / `need`（刚需⭐1-5）/ `use` / `buy` / `pairing` / `stock`（家里有｜待购｜在架）

## 判定规则（前端靠它渲染，不要改语义）

1. "能调" = spirits 全部命中在架 items（名称模糊匹配）且 need 无"（待购）"且该辅料非"待购"
2. 新入一瓶基酒 → 检查是否与现有 mixers/软饮组合出**新配方**，有则同步 append recipes[]（这是本台账的核心价值：入册=解锁喝法）
3. 软饮基底（cat=兑饮基底·软饮）不填 abv 时前端显"0% vol·非酒精"
4. 修改后必跑 `python3 serve.py --check`（数据契约自证），非零退出=你写坏了，修到绿再回复用户

## 写入纪律

- 只增改，不删条目；喝完的把 `stock` 改"已喝完"（历史即数据）
- 日期一律 `YYYY-MM-DD` 绝对格式，禁"昨天/上周"
- 拿不准的字段写"待确认"进 note，前端会挂「信息待补」徽章，不要瞎编
- 原子写：先写 `.tmp` 再 rename，参考 `mcp/barkeeper.py` 里的 `os.replace`

## 典型任务示范

用户："这瓶是朋友送的苦酒（金巴利式 bitter 这一类）" →
你：items 加一条（name=示例苦酒, abv=24, note 记"YYYY-MM-DD 用户拍照入库"），检查 recipes 里该苦酒的组合（Negroni 系）是否可解锁，若缺红威末则 shopping.liquor_advice 更新，跑 --check，回复一张「新解锁配方」表。
