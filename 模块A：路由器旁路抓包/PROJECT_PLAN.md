# 模块 A 项目方案：路由器旁路抓包 → 背包自动同步

> 本文是模块 A 的具体技术方案，供实现与复核使用。
> 面向读者的问题、取舍与结果见 [`README.md`](README.md)；demo 入口为 `live.html`。

## 1. 范围与约定

- **目标**：在网络必经点被动读取游戏流量，产出可查询的战斗、背包、蛋等结构化信息
- **非目标**：不接真实 libpcap、不部署云函数、不实现完整 12 页签看板
- **合规边界**：被动只读，BPF 严格过滤；不发包、不注入、不改内存；原始帧、明文帧、会话密钥不进入交付物；默认不同步

### 三个判断

| 判断 | 决策 | 理由 |
|---|---|---|
| 合规 | 被动只读 + BPF `tcp port 8195 and host <游戏设备IP>` | 划清辅助工具与外挂的界限 |
| 架构 | 抓包与解析拆分，先落 pcap，离线回放解析 | 同步解析大帧会拖垮抓包、导致战斗帧丢失 |
| 隐私 | 默认不同步 + 字段白名单 | 契约层不带 UID / 玩家名 / IP / 时间戳；隐私最小化是设计约束 |

## 2. 系统架构

```
玩家设备 (PC / iPad / 手机)
        │ 网络必经点
路由器 br-lan（混杂模式 + BPF 过滤）
        │ pcap 落盘（原始帧留档，不进产物）
离线回放层：TCP 重组 → 会话解密 → opcode 门控
        │ 契约事件 JSONL（fields 白名单）
结构化派生：战斗 M5 / 背包 M10 / 收蛋 / 连接诊断
        │
用户显式同步（默认关闭）
```

- **采集层**：只负责落盘 pcap，零解析，避免大帧拖慢抓包
- **解析层**：按 flow 重组 TCP 段，使用 `0x1002` 会话密钥解密，按 opcode 分派
- **输出层**：仅输出白名单数值字段与本地 catalog 还原的名字，名字表不含账号信息

## 3. 事件契约

上级项目 `roco_capture/live/protocol/VERSION.json` 与 `core/contract.py` 定义，每行事件 JSON：

| 字段 | 含义 |
|---|---|
| `ts` | 事件时间戳 |
| `flow_id` | TCP 流标识 |
| `dir` | `C2S` / `S2C` |
| `opcode` | 协议命令号 |
| `msg_name` | 可选消息名 |
| `fields` | 白名单数值字段（键为 protobuf field number） |
| `confidence` | `verified` / `community` / `schema` / `unknown`，业务只消费 `verified` |
| `raw_len` | 原始帧长度 |
| `state` | `key_captured` / `decrypt_fail` / `flow_created` / `flow_closed` / `link_lost` |
| `field_confidence` / `unknown` / `unknown_count` | 字段级置信度与未知字段留档 |
| `event_kind` | `m5` / `bag` / `egg` / `diag` 等业务标记 |
| `m5` / `bag` / `egg` / `diag` | 扩展结构，只允许数字与固定 kind 字符串 |

帧格式：`magic 0x3366`、cmd@6（2B BE）、seq@9、hdr_len@13、body_len@17；明文标志 `55AA`；密钥 opcode **4098 = 0x1002**（`header_extra[2:18]`，16B AES-128-CBC）；加密 opcode 16403。

## 4. opcode 门控与字段映射

| opcode | 消息 | 用途 | 关键字段 |
|---|---|---|---|
| 4098 / 0x1002 | 会话密钥 | AES-128 CBC 密钥，只在 TCP 建连瞬间下发 | `header_extra[2:18]` |
| 258 | profile | 账号来源与 `game_id`，用于同 IP 双开区分 | `f1=game_id` |
| 338 | ZoneEnterSceneRsp | 家园 / 学院窝场景，兼作收蛋账号源 | `f4` / `f7` 家具 configId |
| 4886 | ZoneBattleEnterNotify | 战斗进场 | `f1=battle_mode`，`f11=enter_battle_type` |
| 4890 / 4900 / 4908 | 战斗回合 / 施展 / 结束 | M5 战斗卡状态推进 | 4908 `summary.f19=battle_id` 用于同场去重 |
| 4934 | ZoneGetPetInfoByPageRsp | PetData 背包数据 | `f4 → PetDataInfoList → PetData` |
| 6273 / 6275 / 6277 / 6289 | PetBox | 盒位与格子 | 6277 盒位在 `field 2 (tag 0x12)` |
| 579 | ZoneGoodsRewardNotify | 收蛋奖励 | `1.4.1.4.1` 新蛋 id、`...4.2` 蛋道具、`...15.1` petConfId、`...15.3` 体重克 |
| 1044 | 心跳 | 无信息帧，实时链路默认过滤 | 原始 pcap 留档，可通过开关恢复读取 |

`battle_mode`：`0` 无 / `1` 野生交互 PVE / `5` 普通 PVE / `6` PK。
`enter_battle_type`：`1` PVE / `2` 野生 PVE / `11` 花种 / `12` Boss / `22` PVP 排位。

## 5. 结构化信息字段契约

### 5.1 战斗 M5

4886 解密帧嵌套路径：`root.f6=init_info` → `init.f1=battle_id`、`init.f5=本方队伍`、`init.f6=敌方 sides` → `side.f2=单位 wrapper` → `unit.f2=detail`：

| 字段 | 含义 |
|---|---|
| `f2` | game_id |
| `f15` | form_id，战斗内即 pet_id |
| `f3` | 名字（本地表还原） |
| `f7` | nature_id |
| `f10` | level |
| `f45` | mutation_type，bit0 异色 / bit3 炫彩 |
| `f47` | blood_id |
| `f93` | voice，负值需补码 |

4908 用 `summary.f19=battle_id` 回填结束态，避免同场重复计数。

### 5.2 背包 M10

4934 PetData 常用字段：`f5=acquisition_source`、`f7=nature_id`、`f8=gender`、`f26=height_cm`、`f27=weight_g`、`f45=variant_flags`（bit0 异色 / bit3 炫彩 / bit5 未知变体）、`f47=blood_id`、`f82=speciality_id`、`f93=voice`。盒位由 6273 / 6275 / 6277 / 6289 提供。

### 5.3 收蛋

- 收蛋请求：`0x0137`（C2S），字段 `4.1.1` / `4.1.2` 为窝坐标
- 奖励帧：579，需过 `EGG_ITEM_IDS={107010}` + pet + 体重门禁，避免通用奖励误报
- 学院窝判定：窝坐标到 `(-442, 1125)` 距离 ≤ `240√2≈339`；configId `1001072`
- 配对窗口：6 秒

`egg{}` 输出字段：`kind(collect/reward/paired)`、`egg_id`、`item_id`、`pet_id`、`weight_g`、`obtained_ts`、`x`、`y`、`cfg`、`academy`、`dist`、`pair_dt`。

### 5.4 连接诊断

统计 `key_captured` / `decrypt_fail` / `link_lost` 次数、opcode 分布 TOP10、未知字段 TOP10、`event_kind` 与 `confidence`；页面不展示 UID、IP、玩家名与原始帧。

## 6. 路由底层环境与稳定性

- 已验证环境：**新路由 D2（Newifi D2）+ Padavan（老毛子）固件**
- `br-lan` 开混杂模式，`tcpdump` / libpcap 抓桥上流量，不需要厂商 SDK
- `/opt` 挂 Entware，装 `python3` 与采集脚本；tmpfs 固定 256MB
- Padavan 启动脚本会在 USB 重挂时把 `/opt` 打回 40MB：修改 `Sh01_mountopt.sh` + `nvram size_tmpfs=262144` + `started_script.sh` remount，并用 `mtd_storage.sh save` 写入 flash；另备一键恢复脚本
- `gap_timeout` 由 5s 调到 10s：`link_lost` 74 → 10，单场战斗 4886 帧稳定到 3；代价是出卡延迟增加同样秒数

## 7. 关键技术挑战与应对

1. **采集与解析耦合**：实时解析大帧抢占抓包资源，战斗帧 4886 丢失 → 采集层只落 pcap，解析放到离线回放
2. **密钥时序约束**：`0x1002` 只在建连瞬间出现，后续不重发 → 采集先行，再让设备断网 3 秒重连
3. **丢段与噪声帧**：1044 心跳约 14 条/秒，数分钟灌满 5000 条 ring buffer 并把 4886 挤出 → 实时链路过滤无信息帧，原始 pcap 完整留档，支持开关恢复读取被忽略 opcode
4. **多设备与同 IP 双开**：PC / iPad / 手机并行在线 → 按 IP 分发，258 profile 的 `game_id` 区分会话
5. **路由环境偏移**：`/opt` 被重挂打回 40MB → 固化脚本与 nvram，提供自恢复
6. **盒位语义歧义**：出战栏不属于背包盒；场景宝箱 24 格与背包盒 30 格混用；协议 `box_id` 顺序不等于游戏展示顺序 → 仅接受 `box_id∈[1,200]` 且 `len(pet_gids)==30` 且空位在 `[0,30]`；从 rawProtocol 队伍变更帧恢复 3 队 × 6 的 Z 序（109 份历史抓包 108 份完全一致、1 份接近）

## 8. 数据方案与脱敏

- 源：`上级项目/dashboard/assets/boxes_Miffy.json`
- 脱敏：保留昵称 Miffy；去掉 UID、源文件名、`generatedAt` / `sourceTs` / `importedAt` / `obtainedAt` 及坐标字段
- 生成：`scripts/prepare_miffy_data.py` 输出 `data.js`（`window.DEMO_DATA`），可重跑
- 约束：契约层不夹带 UID、玩家名、IP、时间戳；名字仅本地 catalog 还原

## 9. Demo 实现说明与真实 pcap 数据源

`live.html` 是路由器 live 监控页的离线版本：

- **形态**：顶部状态与统计卡、设备筛选、左侧滚动事件流、右侧战斗 / 背包 / 蛋 / Opcode / 未知字段 / 连接诊断面板；不加载原始 pcap、明文帧或会话密钥
- **演示数据源**：真实环境由路由器采集端提供契约事件；演示环境拿不到抓包，因此「回放 pcap」载入从**本地真实 pcap 离线解出**的 14 条关键事件
- **真实抓包规模**：该 pcap 共 10237 帧，解密成功 3869 帧；离线派生 43 盒 / 885 只 / 429 异色 / 101 炫彩 / 83 蛋
- **脱敏**：时间戳改为相对毫秒，去掉 UID / 账号 / IP / 源文件名；m5 去掉 `enemy_side`（UID）与 `game_id`（实例号），宠物名用本地快照表还原
- **交互**：设备筛选、点击行展开完整 JSON、暂停滚动、清空、导出 JSONL；「启动采集」在演示环境下提示未连接路由器
- **右侧联动**：4886 推进战斗卡，4934 + 快照推进背包卡，579 + 蛋背包容器扫描推进收蛋卡，所有事件推进诊断与分布卡

### 再生 `replay_data.js`

原始 pcap 只在本地，不入库；用上级项目解析器生成事件与快照，再由本仓库脚本脱敏裁剪：

```powershell
$ROOT = 'c:\Users\周子涵\CodeBuddy\Roco-dashboard-demo'
$UP   = 'c:\Users\周子涵\CodeBuddy\Roco-dashboard\roco_capture\live'
$PCAP = '<本机真实 pcap 绝对路径>'
$IP   = '<游戏设备IP>'
$PY   = 'C:\Users\周子涵\.workbuddy\binaries\python\versions\3.13.12\python.exe'
$env:PYTHONIOENCODING = 'utf-8'

cd $UP
& $PY run.py --source sources/pcap.py:create_source --source-arg "file=$PCAP" --source-arg "game_pc_ip=$IP" --gap-timeout 10 --drop-opcodes 1044 --out "$env:TEMP\roco_real_events.jsonl"
& $PY pcap_replay.py $PCAP --mode both --game-ip $IP --snapshot-dir "$env:TEMP\roco_real_snap" --settle 0.5

$SNAP = (Get-ChildItem "$env:TEMP\roco_real_snap\*_boxes.json" | Select-Object -First 1).FullName
& $PY "$ROOT\scripts\build_replay_from_pcap.py" --events "$env:TEMP\roco_real_events.jsonl" --snapshot $SNAP --out "$ROOT\模块A：路由器旁路抓包\replay_data.js"
```

若 `pcap_replay.py` 报尾部截断，先在 `$env:TEMP` 里复制一份裁掉末帧头的 pcap 再跑；裁切文件同样不入库。

## 10. 实施步骤与验证清单

1. 写脱敏脚本，生成并校验 `data.js`
2. 搭 live 监控页骨架与视觉样式
3. 实现回放事件流与滚动日志
4. 实现右侧对战 / 背包 / 蛋 / 诊断面板
5. 实现设备筛选、导出 JSONL 与清空
6. 写模块 README 与本文
7. 验证：JS 语法、脱敏泄漏、统计一致、DOM 引用、浏览器打开无报错

- [x] `node --check` 通过
- [ ] 数据中无 UID / 精确时间戳
- [ ] 统计与源快照一致（26 / 593 / 187 / 84）
- [ ] DOM 引用无缺失
- [ ] 浏览器实际打开无报错

## 11. 真实度标注

| 内容 | 真实度 |
|---|---|
| 数据结构与统计 | 真实快照脱敏 |
| 链路 / opcode / 合规红线 | 来自上级项目真实实现与文档 |
| 抓包 / 解密过程 | 回放事件按上级项目契约与 fixture 字段构造，未接真实 libpcap |
| UI | 参照上级项目 live 页形态新做 |
