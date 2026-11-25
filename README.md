# Roco-dashboard-demo

把上级项目 `Roco-dashboard`（《洛克王国：世界》异色精灵统计看板）里的真实技术链路，拆成若干**可运行的小 demo**，沉淀可复用的抓包、解析与数据派生方案。

> GitHub 仓库：https://github.com/Zane0207/roco-dashboard-demo
> 当前状态：模块 A / B 均已有可离线运行的 demo。每个 demo 都从真实项目里来，但只保留可公开、可离线运行的部分。

## 1. 问题来源

以真实玩家 Miffy 的账号为例：**26 个盒子、593 只精灵，其中 187 只异色、84 只炫彩**。游戏没有导出能力，确认资产分布只能逐页浏览。数据已经存在，但不可查询。

## 2. 目标与边界

将不可见的游戏数据转化为可结构化查询的资产，同时满足：不接触游戏进程、不给每台终端设备增加安装负担、数据所有权始终归用户。

## 3. 行业常见方案

- Windows 侧：[Npcap](https://nmap.org/npcap/) / [WinPcap](https://www.winpcap.org/) 配合 [Wireshark](https://www.wireshark.org/)，需要内核驱动与管理员权限
- 移动端：[Charles](https://www.charlesproxy.com/)、[HttpCanary](https://httpcanary.cn/) 依赖证书与系统 VPN；[PCAPdroid](https://github.com/GrenderG/PCAPdroid) 可免 root 抓包；root / 越狱后可使用 [tcpdump](https://www.tcpdump.org/)
- 同场景项目：[ROCO-Nearby-Pet](https://github.com/Vicuna1277/ROCO-Nearby-Pet)（附近精灵查看）与 [roco-pve-viewer](https://github.com/Evenstar-tools/roco-pve-viewer)（PVE 战斗查看）也能读取游戏数据，但聚焦单机 / 单端展示，不具备跨设备统一采集

## 4. 方案局限

这些方案都能抓包，但成本落在每台终端设备上：每机一套配置、时间线对不齐、导出格式不统一。抓包能力分散，无法沉淀为统一数据源，上层应用需重复开发。

## 5. 技术路径

采用网络旁路采集架构，将抓包点迁移至**网络必经点——路由器**：端点零安装，`br-lan` 上 BPF 严格过滤游戏流量，先落 pcap、离线再解析。单份原始数据可同时派生背包、战斗、图鉴等多套应用。

底层已在**新路由 D2（Newifi D2）+ Padavan 固件**上验证：Entware 提供 `tcpdump` / `python3`，`/opt` 固定 256MB tmpfs；端点侧零安装。

## 6. 关键挑战与应对

| 挑战 | 应对 |
|---|---|
| 采集与解析耦合导致战斗帧丢失 | 采集/解析解耦，先落 pcap，离线回放解析 |
| `0x1002` 仅在建连瞬间下发 | 采集先行，断网 3 秒重连触发密钥 |
| 丢段与 1044 心跳噪声淹没战斗帧 | `gap_timeout` 5s → 10s；实时过滤噪声，原始 pcap 完整留档且可恢复读取 |
| 多设备与同 IP 双开 | 按 IP 分发，`game_id` 区分会话 |
| 固件重挂导致 `/opt` 由 256MB 回落至 40MB | 固化启动脚本与 nvram，提供一键恢复 |
| 出战栏 / 场景宝箱与背包盒混淆 | 盒位判别式 + 抓包队伍序列还原显示顺序 |

完整过程见模块 A 的 `PROJECT_PLAN.md`；识别 → 推荐 → 图鉴链路见模块 B 的 `README.md`。

## 7. 结果与价值

- **资产可见性**：26 盒 / 593 只 / 187 异色 / 84 炫彩，玩家核心资产首次可查询
- **链路复用性**：PC + iPad + 手机统一采集；一次抓包，多处派生
- **扩展成本**：新增应用只写离线解析器，不再改动抓包链路与终端设备
- **数据边界**：原始帧与会话密钥不出本机，交付物仅含脱敏派生字段

## 模块清单

| 模块 | 主题 | 状态 |
|---|---|---|
| A | 路由器旁路抓包 → 背包自动同步 | 🚧 实现中（`模块A：路由器旁路抓包/`） |
| B | 阵容识别 → 性格推荐 → 图鉴链路 | ✅ 已完成（`模块B：阵容识别与性格推荐/`） |
| C | 蛋窝决策助手 | ⏳ 待做 |
| D | 毕业进度仪表盘 | ⏳ 待做 |

## 快速开始

模块 A 目录：`模块A：路由器旁路抓包/`

- `README.md` — 模块说明（问题来源 / 目标与边界 / 行业常见方案 / 方案局限 / 技术路径 / 关键挑战与应对 / 结果与价值）
- `PROJECT_PLAN.md` — 具体项目方案（事件契约 / opcode 字段映射 / 稳定性处理 / 验证清单）
- `live.html` — 路由器 live 监控页的离线版本，演示时回放从真实 pcap 解出的事件
- `replay_data.js` — 真实 pcap 派生的脱敏事件与背包 / 蛋快照
- `data.js` — 脱敏后的 Miffy 背包快照（问题来源示例）
- `scripts/prepare_miffy_data.py` / `scripts/build_replay_from_pcap.py` — 数据再生脚本

模块 B 目录：`模块B：阵容识别与性格推荐/`

- `README.md` — 模块说明（问题来源 / 目标与边界 / 行业常见方案 / 方案局限 / 技术路径 / 关键挑战与应对 / 结果与价值）
- `PLAN.md` — 实施计划与验证清单
- `PROJECT_PLAN.md` — 字段契约、真源与数据口径
- `live.html` — 一图流识别 demo，切换两份真实 OCR 缓存样例后按 6 阶段回放
- `data.js` — 脱敏后的 OCR dets / 识别结论 / 性格与推荐 / 图鉴字段
- `scripts/prepare_team_data.py` — 数据再生脚本

两份 `live.html` 都是双击打开即用，无需服务器、无需联网、零依赖。

## 公共约定

- 主源码：每个模块的 HTML 入口（`live.html`，单文件、内联样式与脚本）
- 数据：模块目录下的 `data.js`（脱敏后的真实数据）
- 生成脚本：`scripts/` 下与上级项目快照对接的工具
- 视觉：深色科技感 + 紫粉渐变，两个模块共用同一套 CSS token

## 当前进度

- [x] 调整项目说明，建立 GitHub 仓库
- [ ] 模块 A：按 `PROJECT_PLAN.md` 完成交互与验证
- [x] 模块 B：按 `PLAN.md` 完成交互与验证
- [ ] 模块 C / D：待启动
