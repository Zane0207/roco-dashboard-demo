# 模块 B 项目方案：字段契约、真源与数据口径

> 本文是模块 B 的技术/detail 说明，供实现与复核使用。
> 面向读者的问题、取舍与结果见 [`README.md`](README.md)，实施与验证见 [`PLAN.md`](PLAN.md)。

## 1. 范围与约定

- **目标**：一图流 dets → 6 格阵容 → 性格反查 → gradRec 比对 → 图鉴字段回链
- **非目标**：不接腾讯云 OCR、不部署云函数、不上传原图、不修改识别结论
- **合规边界**：只消费 OCR 文本框；原图、明文网络帧、会话密钥、UID / IP / 昵称不进产物

## 2. 真实 OCR 契约

上级项目 `cloudfunctions/teamOcr/index.js` 的输入输出（demo 只消费 dets 与结论，不重跑云函数）：

```text
请求：canvas 压长边 ≤2000px → base64 → {op:'push',uploadId,idx,total,data}（55KB/块）
响应：{ok,engine,elapsed,cells:[{row,col,name,char,gain,loss,quals[3],skills[4]}]}
cells 按 Z 序排列；失败返回 {ok:false,error}
```

`dets` 单条结构：

| 字段 | 含义 |
|---|---|
| `x1/y1/x2/y2` | 文本框左上角 / 右下角坐标 |
| `text` | OCR 识别字符串（可能含水印、资质串、错字） |
| `score` | OCR 置信度 |

demo 的 `live.html` 按 `board.w/h = max(x2/y2)+40` 把 bbox 等比例画到示意网格上，**不加载原图**。

## 3. 识别语义层

### 3.1 锚点顺序

- 按 `cy` 聚行 → 行内取整行命中 → 按行内元素数降序拼够 6 → 按 `(cy,cx)` 恢复 Z 序
- 两份样例的 6 格顺序直接取自 `scripts/selftest_teamocr.js` 第 8 / 9 节断言，不在 demo 里重新排序

### 3.2 名字归一

顺序：`exact → fuzzy → shape → prefix`。

- 候选池：`cloudfunctions/teamOcr/pool_names.json`，真源是 `_pets.json` 基础名（不再混入 PVP 助手 / 测试名）
- `prefix` 兜底约束：图鉴名 ≥3 字、必须整框开头、整体未被 exact/fuzzy 命中、取最长匹配名
- 典型样本：「卡瓦重噜球狼王」→ 卡瓦重（`from=prefix`）；「恶魔狼王」仍走 exact，不被前缀误伤

### 3.3 性格反查

- 真源：`cloudfunctions/teamOcr/natures.js`，由 `性格表.csv` 生成，30 条 `(nature, gain, loss)`
- 组合唯一，`(增益, 减益)` 可确定性反查性格
- 模板 A（2 行 3 列）直接 OCR 出性格名；模板 B（3 行 2 列）只读到两个属性框，走反查
- 示例：`速度↑ / 魔攻↓ → 开朗`、`物攻↑ / 魔攻↓ → 固执`、`魔攻↑ / 物攻↓ → 聪明`

### 3.4 技能与资质

- 技能框归属：名字 `cx` 向右 300–440px，`[cx-80, cx+colGap×0.8]`，半径固定 300px
- 技能池：`pool_skills.json`，真源是 `pet_skills.json` 的 `name`
- 池外文本（如「筛管窝流」）在 demo 中保留原文并标 `!`，说明正式输出会按池过滤
- 资质串：`个体资质` 右侧 3 个属性；属性串与标签词不得进入名字候选

## 4. 推荐与图鉴口径

### 4.1 gradRec

- 真源在云端 `gradRec` 集合（云函数 `recEdit`），demo 只读离线快照 `dashboard/grad_rec.json.bare_bak`
- demo 消费列：图鉴编号 / 最终形态 / 性格 / 推荐等级 / 个体资质
- 只取带性格的推荐行；按 `(性格, 等级)` 去重，优先保留带资质描述的行
- 同一最终形态有多口径时全部展示（毕业 / 可用 / 收藏），命中当前性格的项高亮
- 同编号别名：`圣剑-X` ↔ `X_圣剑`（图鉴编号 286），在生成脚本里显式登记

### 4.2 图鉴回链

来自 `dashboard/_pets.json`：

| 字段 | 用途 |
|---|---|
| `pet_id` | 图鉴主键，头像按 gtimg `jingling/<id>/icon.png`、立绘按 shallow `pets/<id>/icon.png` 定位 |
| `handbook_no` | 图鉴编号，与推荐表 dex 对齐 |
| `egg_group_names` | 蛋组；按项目约定将 `岩石组` 归一为 `大地组` |
| `gender_ratio` | 性别比例（真源，不用 `pets_api.json` 的 `sex`） |
| `season_id` / `has_shiny` | 赛季与异色官方图标标记 |

demo 只显示这些字段的文本与路径模式，**不发起任何外部图片请求**。

## 5. 脱敏与再生

- 输入全部只读，产物只写 `模块B：阵容识别与性格推荐/data.js`
- `data.js` 形态：`window.TEAM_DEMO_DATA = {...}`；含 `meta / natures / samples`
- `scripts/prepare_team_data.py` 可重跑；断言性格表 30 条、图鉴条目存在；OCR 样本带 BOM 时用 `utf-8-sig`
- 不写入：原图、玩家昵称、UID、设备 IP、端口、精确时间戳、会话密钥、明文帧

## 6. 真源与产物对照

| 内容 | 上级项目真源 | demo 产物 |
|---|---|---|
| OCR 文本框 | `scripts/testdata/ocr_real_sample_3col.json` / `ocr_real_sample_wolf.json` | `samples[].dets` |
| 6 格结论 | `scripts/selftest_teamocr.js` 第 8 / 9 节 | `samples[].cells` |
| 性格表 | `cloudfunctions/teamOcr/natures.js` ← `性格表.csv` | `natures` |
| 名字 / 技能池 | `pool_names.json` / `pool_skills.json` | `meta.poolNames / poolSkills` + 每格 `inNamePool / skills[].inPool` |
| 推荐 | `dashboard/grad_rec.json.bare_bak` | `cells[].recs` |
| 图鉴 | `dashboard/_pets.json` | `cells[].codex` |
