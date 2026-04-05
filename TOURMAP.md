# TOURMAP（项目进度地图）

模块关系与数据真源见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)；各目录内文件说明见对应 `README.md`。

## DONE（已完成）

- [x] **知识图谱参与 Input 压缩**
  - 将图谱相关信息纳入章节生成前的上下文压缩逻辑，减少无关冗余注入。
  - 手动时间线/事件归属场景下，避免把跨章历史状态整包塞入，降低“状态串章污染”。

- [x] **前后端工作流改造为“先预览、后运行”**
  - 主按钮先生成 Input 预览，再由弹窗“确认并运行”触发流式生成。
  - 运行链路中增加更明确的阶段提示（规划 -> 写作 -> 保存 -> 下章建议）。

- [x] **图谱展示与编辑能力增强（可视化层）**
  - 图谱改为全屏查看入口，提升复杂关系图可读性。
  - 支持节点/边关系编辑、关系删除、时间线前后关系调整等交互能力。
  - 时间线“未安排上/下一跳”支持更直观标识，方便排查断点。

- [x] **存储结构从单状态向表结构演进**
  - 章节、事件、人物相关数据逐步拆分，减少单一叙事快照作为唯一真源的耦合；持久化现为 `storage/novels/<id>/novel.db`（`novel_state`、章节行、四表等）。
  - 运行前预构建章节关联记录，保证“章节属于事件、关联人物”先落地再生成正文。

- [x] **单本小说 SQLite 落地**
  - 图谱与章节编辑仍走 `graph_tables` / `storage` 原 API，底层由 `novel_sqlite` 写入 `novel.db`。

- [x] **Electron Windows 安装包（NSIS + PyInstaller 后端）**
  - 一键脚本 `build-windows-release.bat`；安装版数据在 exe 同级 `data/`；Web 内首次引导、打开输入/输出目录；详见 [electron/ELECTRON_RELEASE.md](../electron/ELECTRON_RELEASE.md)。

- [x] **流式输出与右侧面板体验优化**
  - 右侧状态文案对齐当前真实流程（移除 auto_init 误导信息）。
  - 规划流/正文流/下章建议的空态提示改为运行态动态提示。
  - 右侧输出新增**自动滚动到底**，无需手动拖动滚动条。

- [x] **前端文学暖色主题与续章流程**
  - `theme-literary.css`：纸感背景、Element 变量、顶栏与弹窗样式；`Noto Serif SC`（`index.html`）。
  - 写作/优化等结束后「下章提示」弹窗 → 与「生成正文」相同的 Input 预览链。
  - 表单可选「当前地图」→ `RunModeRequest.current_map` → `build_llm_user_task` 注入约束。

## TODO（待完成）

- [ ] **Electron 安装包持续维护**
  - 发布流程与踩坑记录：[electron/ELECTRON_RELEASE.md](../electron/ELECTRON_RELEASE.md)；详细参数见 [electron/README.md](../electron/README.md)、[packaging/pyinstaller/README.md](../packaging/pyinstaller/README.md)。
  - 构建产物勿入库：见根目录 `.gitignore`（`electron/release/`、`dist/`、`novel-backend.spec`、内置 `novel-backend.exe` 等）。

- [ ] **知识图谱可视化继续重构完善**
  - 优化大图性能（节点多时布局、缩放、渲染帧率）。
  - 补充批量编辑/过滤视图（按章节、按角色、按事件类型）。
  - 强化边编辑的可解释性（来源、修改历史、冲突提示）。