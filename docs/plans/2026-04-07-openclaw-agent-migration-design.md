# OpenClaw Agent Migration Design

Date: 2026-04-07

## Goal

放弃当前“自定义 agent 兼容层优先”的设计，全面迁移到以最新 OpenClaw agent 设计为目标的后端架构。

这里的“迁移”不是把现有 task/workflow 外面再包一层新 API，而是重设系统主轴：

1. `gateway` 成为 session 与 agent 运行时的唯一真相源。
2. `session` / `run` / `agent workspace` 成为一等模型。
3. `video_thread` / `iteration` / `task` 退回到视频域执行层，而不是承担 agent 控制面。
4. memory 从“隐式 prompt 注入的数据库摘要”迁移到“可检索、可审计、跨 session 的显式记忆层”。

## 目标架构依据

本设计以 OpenClaw 当前官方文档为准，核心约束来自以下页面：

1. [Gateway Architecture](https://docs.openclaw.ai/concepts/architecture)
2. [Session Management](https://docs.openclaw.ai/concepts/session)
3. [Delegate Architecture](https://docs.openclaw.ai/concepts/delegate-architecture)
4. [Memory Overview](https://docs.openclaw.ai/concepts/memory)

从这些官方资料里，可以提炼出四个稳定事实：

### 1. Gateway 是唯一控制面

OpenClaw 把 gateway 定义为单一长生命周期进程：

1. 统一持有消息入口与控制面连接。
2. 控制面客户端通过 WebSocket 接入 gateway。
3. session 状态由 gateway 持有，而不是分散在 transport、tool 层或业务服务里。

这意味着当前仓库里 `FastMCP ctx -> session_key`、`HTTP auth session`、`SessionMemoryRegistry` 三处分裂持有 session 真相的方式，方向上与 OpenClaw 不一致。

### 2. Session 由来源路由，而不是由认证附带

OpenClaw 的 session 不是“谁登录了就拿谁的 session token”，而是“消息从哪里来，就路由到哪个 session”：

1. DM 默认共享一个连续 session。
2. 群聊按房间隔离 session。
3. cron/job 每次运行创建新 session。
4. session 生命周期由 gateway reset/idle 策略管理。

这与当前项目里“HTTP agent session”“MCP transport session”“task.session_id”三套混合语义不同。

### 3. Agent 是带 workspace / agentDir / tool policy 的命名实体

OpenClaw delegate 不是单纯的 `agent_id + token`，而是具备：

1. 独立 `workspace`
2. 独立 `agentDir`
3. 显式 `tools.allow`
4. 渠道路由绑定
5. 作为 delegate/assistant 的命名身份

而当前项目的 `agent_profile` 更偏向：

1. 身份认证
2. 默认渲染/风格参数
3. 学习与策略建议

这不足以表达 OpenClaw 风格 agent runtime。

### 4. Memory 是显式工具化能力，不是隐式数据库摘要

OpenClaw memory 的重心是：

1. workspace 内记忆文件
2. `memory_search` / `memory_get` 等工具
3. 跨 session 检索
4. 后台 consolidation / flush

当前项目的 `session_memory_service` 与 `persistent_memory_service` 已有“短期/长期”概念，但仍然主要服务于 task prompt 注入，不是 gateway/agent runtime 主导的显式记忆模型。

## 当前仓库现状

当前仓库已经不是简单视频工具，而是较完整的 agent-ish 平台：

1. 认证：`agent_profile` / `agent_token` / `agent_session`
2. 短期记忆：`session_memory`
3. 长期记忆：`persistent_memory`
4. 协作：`workflow_participants` / `multi_agent_workflow_service`
5. 线程运行时：`video_thread` / `video_iteration` / `video_turn` / `video_agent_run`
6. 协议面：FastMCP + HTTP API
7. 执行面：task service + worker + workflow engine

这说明迁移应该利用已有 thread/run/domain 基础，而不是盲目重写视频执行层。

## 关键差距

### 差距 1：Session 真相源分裂

当前：

1. HTTP 用 `AgentSessionService`
2. MCP 用 `session_key_for_context(...)`
3. memory 再用 `SessionMemoryRegistry`

目标：

1. 统一由 gateway session service 路由与分配 session
2. transport 只提供来源线索
3. memory 订阅 gateway session，而不是反过来生成 session

### 差距 2：Agent 模型偏认证，不偏 runtime

当前 agent 重点是：

1. 鉴权
2. profile patch
3. token override

目标 agent 重点应是：

1. workspace
2. agentDir
3. tool capabilities
4. channel/delegate routing
5. run ownership

### 差距 3：Task 仍然承载过多 agent 控制语义

虽然当前已有 thread-first runtime，但以下语义仍大量落在 task 上：

1. memory 注入
2. review / repair loop 入口
3. 协作控制
4. ownership

目标状态应是：

1. gateway/session/run 持有 agent 控制真相
2. `video_thread` 持有产品协作真相
3. `task` 只持有视频执行真相

### 差距 4：Memory 仍是 task-centric

当前 memory 更像：

1. 面向 revise/retry 的上下文摘要
2. 存在数据库快照与 agent memory record
3. 自动拼进 prompt

目标 memory 更像：

1. agent workspace 知识面
2. 显式搜索/读取工具
3. 可跨 session 复用
4. task 只消费记忆结果，而不是拥有记忆系统

## 迁移原则

### 1. 明确破坏兼容

本次迁移不再以兼容现有 agent 设计为目标，允许：

1. 重命名核心抽象
2. 逐步废弃旧 HTTP/MCP agent surface
3. 迁移期间保留桥接层，但桥接层不是目标架构

### 2. Gateway-first

先统一 gateway/session/run，再动 workflow 细节。否则只是继续在 task 层叠更多 agent 逻辑。

### 3. Thread-first, Task-second

当前仓库已有 `video_thread` 基础，这一层比旧 task-centric 协作模型更接近 OpenClaw 的会话/运行视角，应作为承接点保留并增强。

### 4. Memory toolization

逐步停止“自动注入一大段 memory summary”作为主路径，改为：

1. session 记忆用于短窗口 continuity
2. workspace / long-term memory 通过显式检索接入

## 目标模型映射

| 当前仓库 | OpenClaw 目标 | 迁移策略 |
| --- | --- | --- |
| `AgentProfile` | named agent definition | 保留部分配置，迁移为 agent runtime definition |
| `AgentSession` | gateway-routed session binding | 降级为控制面认证记录，不再主导业务 session |
| `SessionMemoryRegistry` | gateway-owned session state + short-term memory | 由 gateway session service 驱动 |
| `PersistentMemoryService` | memory tools / workspace memory backend | 逐步从 prompt 注入改为显式检索 |
| `VideoThread` | session-adjacent collaboration object | 继续保留并增强 |
| `VideoAgentRun` | agent run | 升格为 gateway/runtime 对齐的 run 记录 |
| `VideoTask` | execution task | 收缩为视频执行事实 |

## 分阶段迁移

### Phase 1：Gateway Session Foundation

建立 OpenClaw 风格的 gateway session 层：

1. 新增 gateway session route model
2. 新增统一 session reset policy
3. 让 MCP / HTTP / thread runtime 通过同一入口解析 session

### Phase 2：Agent Runtime Definition

建立命名 agent 定义层：

1. `workspace`
2. `agent_dir`
3. `tools_allow`
4. delegate routing metadata

完成标准：

1. runtime definition 有独立存储，而不是塞进 `agent_profile`
2. identity/authenticate 返回的 principal 直接携带 runtime definition
3. 管理 CLI 默认创建显式 runtime definition
4. 旧 profile 数据只通过受控 bridge materialization 过渡，不再是目标模型

### Phase 3：Run-Centric Orchestration

把现有 `video_agent_run` 升级成 agent runtime 主轴：

1. run 生命周期
2. run 与 iteration/task 的绑定
3. 多 agent/ delegate 执行入口

当前阶段先完成最小版：

1. 新增独立于 `video_agent_runs` 的控制面 `agent_runtime_runs`
2. 在鉴权和任务入口上落 runtime run 记录
3. 明确区分“OpenClaw 控制面 run”与“视频线程执行 run”

### Phase 4：Memory Rebase

重做 memory 接入策略：

1. 短期 continuity 继续绑定 session
2. 长期 memory 迁移到显式检索
3. 减少 task prompt 的隐式 memory 注入

当前已完成的 Memory Rebase 中间态：

1. `VideoTask` 新增结构化 `task_memory_context`
2. `PersistentMemoryService.resolve_memory_context(...)` 现在返回显式 `items`
3. 子任务落库时会保存 `session` / `persistent` 两段结构化 memory context
4. prompt builder、auto-repair、workflow collaboration 已优先消费结构化 memory context
5. root task / child task / workflow memory pinning 现在都先写 `task_memory_context`，再镜像 legacy 字段
6. `task snapshot` / HTTP API / review bundle 已系统暴露结构化 `task_memory_context`
7. 原 `memory_context_summary` / `persistent_memory_context_summary` / `selected_memory_ids` 仍保留为兼容镜像，不再是目标模型

Phase 4 尚未完全结束，剩余清理面包括：

1. SQLite 仍保留 legacy memory 摘要列，尚未进一步收缩 schema 级兼容投影
2. repair / workflow 周边仍保留旧摘要字段兜底路径，后续应继续下沉为迁移桥接层
3. legacy mirror 字段何时可以彻底移除，还取决于外部消费者是否完成迁移

### Phase 5：Legacy Surface Removal

清理旧兼容层：

1. 旧式 agent-centric HTTP 路由
2. transport-specific session 拼装逻辑
3. 过时的 workflow participant 兼容路径
4. 启动期 / 请求期 runtime materialization compatibility layer
5. task-level legacy memory summary 主路径

当前 Phase 5 已完成的切口：

1. `AgentRuntimeDefinitionService.resolve(...)` 不再按需 materialize runtime definition
2. `create_app_context(...)` 不再在启动时 backfill 缺失的 runtime definition
3. HTTP / MCP 新增回归覆盖，验证 gateway session id 在鉴权、task、runtime run 之间保持一致

Phase 5 当前剩余：

1. 继续减少 transport-specific auth cache 的中心性
2. 最终移除不再需要的 legacy HTTP/agent surface
3. 在外部消费者迁移完成后，删除 task-level legacy memory mirrors

## 第一刀实现范围

本轮先做 Phase 1，不直接重写整个 workflow engine。原因：

1. session 真相源是后续所有迁移的基础
2. 当前 `video_thread` / `video_agent_run` 已经足够承接下一阶段
3. 直接动 workflow engine 风险过高，且会把“架构迁移”变成“业务回归修 bug”

本轮完成后，应达到：

1. 新的 gateway session 服务存在且有测试
2. MCP / HTTP 不再各自偷偷生成业务 session
3. `SessionMemoryRegistry` 只消费已解析 session_id
4. 后续 agent runtime / memory 重构有稳定切口
