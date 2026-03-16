# Agent Persistent Memory Foundation 设计

## 1. 目标
在已经完成的多 agent token 身份隔离与 `session-only memory` 之上，为 `easy-manim` 增加一层**可审计、可显式选择、可跨 session 复用**的持久记忆基础层。

第一版的目标非常明确：

1. 持久记忆采用**独立存储层**，不直接揉进 `agent_profiles`。
2. 持久记忆只通过**显式 promote** 从当前 session memory 生成。
3. 每次 promote 生成**一条不可变快照**。
4. 后续请求只有在显式传入 `memory_ids` 时才会使用持久记忆。
5. 第一版只允许在 `create_video_task(...)` 和 `revise_video_task(...)` 中使用持久记忆。
6. `memo0` 与 `embedding` 可以作为可选增强能力，但基础能力不能依赖它们。

该阶段的重点不是做“自动学习系统”，而是先建立一个 agent 可控、服务端可回放、后续可扩展的持久记忆底座。

## 2. 非目标
第一版明确不做以下内容：

1. 自动把成功任务沉淀为长期记忆。
2. 自动从持久记忆中检索并注入到请求。
3. 直接把长期记忆写回 `agent_profiles.profile_json`。
4. 原地编辑某条持久记忆。
5. 对 `retry` 与 `auto-repair` 路径自动或显式注入持久记忆。
6. 强依赖 `memo0`、向量数据库或 embedding provider 才能工作。

这版要解决的是“持久化、选择性复用、审计可回放”，不是“偏好进化闭环”。

## 3. 推荐架构

### 3.1 分层模型
推荐采用三层 memory 分离，而不是把所有记忆概念混在一起：

1. `Session Memory`
   当前已经存在的短期会话记忆，只在 live MCP session 内生效。
2. `Persistent Agent Memory`
   本阶段新增的持久记忆快照仓库，面向跨 session 复用。
3. `Optional Enhancement Layer`
   可选的 `memo0 / embedding` 增强层，用于改进检索、索引或摘要体验，但不改变主流程正确性。

这样设计的好处是：

1. `session memory` 继续保持严格按 `session_id` 隔离。
2. 持久记忆不会污染 `agent profile`。
3. 后续如果要加自动 promote 或智能检索，只需在持久层之上扩展，不需要推翻当前实现。

### 3.2 Promote 流程
持久记忆的唯一入口是显式 promote：

1. 调用 `promote_session_memory()`
2. 从当前 session 读取结构化 summary
3. 生成一条不可变持久记忆记录
4. 返回新的 `memory_id`

该流程不会修改 `session memory`，也不会自动写回 `agent profile`。

## 4. 数据模型

### 4.1 `agent_memories`
建议新增独立表 `agent_memories`，建议字段如下：

1. `memory_id`
2. `agent_id`
3. `source_session_id`
4. `status`
5. `summary_text`
6. `summary_digest`
7. `lineage_refs_json`
8. `snapshot_json`
9. `enhancement_json`
10. `created_at`
11. `disabled_at`

字段职责：

1. `status`
   第一版只需要 `active | disabled`
2. `summary_text`
   面向 prompt 注入的紧凑文本
3. `summary_digest`
   用于去重、比对和调试
4. `lineage_refs_json`
   保留被 promote 记忆所对应的任务线引用
5. `snapshot_json`
   保留完整结构化快照，供审计、调试与未来迁移使用
6. `enhancement_json`
   只在启用 `memo0 / embedding` 增强时记录附加状态，例如 provider、索引引用、增强结果

### 4.2 不可变快照
每条持久记忆在 promote 后即固定，不允许原地改写。

允许的后续状态变更只有：

1. `active -> disabled`

不允许：

1. 修改 `summary_text`
2. 修改 `snapshot_json`
3. 修改 `lineage_refs_json`

这样可以保证：

1. 被某个任务引用过的持久记忆永远可回放
2. 审计时不会出现“同一个 `memory_id` 内容后来变了”的问题

## 5. Tool 设计
第一版推荐只开放四个 MCP tools。

### 5.1 `promote_session_memory()`
作用：

1. 读取当前 session 的 summary
2. 生成一条新的持久记忆记录
3. 返回 `memory_id`

约束：

1. 当前 session summary 为空时返回 `agent_memory_empty_session`
2. 在 `auth_mode=required` 下只能为当前 agent 创建持久记忆
3. promote 后记录默认为 `active`

### 5.2 `list_agent_memories()`
作用：

1. 列出当前 agent 的持久记忆
2. 默认只返回 `active`
3. 可以预留 `include_disabled` 之类的轻量过滤参数

### 5.3 `get_agent_memory(memory_id)`
作用：

1. 返回某条持久记忆详情
2. 包含 `summary_text`、`lineage_refs`、`snapshot`、`status`

### 5.4 `disable_agent_memory(memory_id)`
作用：

1. 将一条持久记忆标记为 `disabled`
2. 停用后不能再被 `memory_ids` 引用使用
3. 不物理删除记录

## 6. 请求接入策略

### 6.1 显式 `memory_ids`
第一版在以下接口上新增：

1. `create_video_task(..., memory_ids: list[str] | None = None)`
2. `revise_video_task(..., memory_ids: list[str] | None = None)`

系统只会读取被显式点名的持久记忆。

如果未传 `memory_ids`：

1. 完全不注入持久记忆
2. 不做自动检索
3. 不从当前 agent 的持久记忆列表里做默认选择

### 6.2 校验规则
服务端在解析 `memory_ids` 时必须校验：

1. 该 `memory_id` 存在
2. 该记录属于当前 agent
3. 该记录状态为 `active`

若任一条件不满足，返回对应错误：

1. `agent_memory_not_found`
2. `agent_memory_forbidden`
3. `agent_memory_disabled`

### 6.3 Prompt 注入
通过校验后，把多条持久记忆的 `summary_text` 组合成一个 `persistent_memory_context`。

推荐注入方式：

1. 在 prompt 中单独增加 `Persistent memory context: ...`
2. 与现有 `Session memory context: ...` 分开，避免混淆
3. 同时把 `memory_ids` 与组合后的摘要写回任务元数据，便于回放

## 7. 与现有 session memory 的关系
持久记忆不是 `session memory` 的替代物，而是其上层抽象。

本阶段的推荐关系：

1. `session memory`
   继续服务 `revise / retry / auto-repair` 的短期上下文
2. `persistent memory`
   仅在 `create / revise` 中按 `memory_ids` 显式带入

这样带来的收益是：

1. `auto-repair` 仍然保持针对当前失败链路的局部修复语义
2. `persistent memory` 则更适合承载“可复用经验”
3. 两者不会在第一版里互相污染

## 8. 可选增强层：`memo0 / embedding`
`memo0` 与 embedding 在本设计中属于**可选增强**，不是基础依赖。

### 8.1 基础原则
必须满足：

1. 在完全不启用 `memo0 / embedding` 的情况下，持久记忆主流程仍然完整可用
2. 增强层不可用时，`promote_session_memory()` 仍然应成功写入基础快照
3. 增强失败只以状态字段或附加信息返回，不应让基础 promote 失败

### 8.2 可选配置
后续可以在 `Settings` 中预留：

1. `persistent_memory_backend = local | memo0`
2. `persistent_memory_enable_embeddings = true | false`
3. `persistent_memory_embedding_provider`
4. `persistent_memory_embedding_model`

### 8.3 可选增强能力
增强层可用于：

1. 为持久记忆生成更丰富的索引信息
2. 保存外部 memory 引擎引用
3. 为未来半自动检索做准备

但第一版不做自动检索，也不改变“只有显式 `memory_ids` 才会生效”的规则。

## 9. 错误模型
建议新增独立错误码：

1. `agent_memory_not_found`
2. `agent_memory_disabled`
3. `agent_memory_forbidden`
4. `agent_memory_empty_session`
5. `agent_memory_enhancement_unavailable`

其中：

1. 前四类属于主流程错误，应直接返回
2. `agent_memory_enhancement_unavailable` 只在启用增强层时出现，而且应作为附加状态或 warning，而不是主流程失败原因

这样可以保持：

1. 基础持久记忆流程明确、稳定
2. 增强层故障不会拖垮主流程

## 10. 推荐实施顺序
推荐分三步推进。

### Phase A：基础持久层
目标：

1. 落 `agent_memories` 数据模型与存储接口
2. 实现 `promote / list / get / disable`
3. 保证 agent 隔离与软停用

### Phase B：请求级显式接入
目标：

1. 为 `create_video_task` 与 `revise_video_task` 增加 `memory_ids`
2. 校验并组合持久记忆摘要
3. 将使用过的 `memory_ids` 回写到任务元数据

### Phase C：可选增强层
目标：

1. 增加 `memo0 / embedding` 配置
2. 做 best-effort 增强适配
3. 保持增强层不可用时主流程依旧正常

## 11. 测试策略
至少应覆盖以下测试：

1. 不同 agent 之间不能读取彼此的持久记忆
2. `promote_session_memory()` 在空 session 上返回稳定错误
3. `disable_agent_memory()` 后该记忆不能再被请求使用
4. `create / revise` 显式传 `memory_ids` 时能正确注入持久记忆
5. 未传 `memory_ids` 时，不会被持久记忆污染
6. 增强层不可用时，基础持久化仍然成功

## 12. 结论
下一阶段最合适的方向，不是直接做“自动学习 agent 偏好”，而是先加一层**独立、不可变、显式 promote、显式选择、带可选增强层的持久记忆基础设施**。

它与当前已经完成的 `session-only memory` 能自然衔接，又为后续的跨 session 复用、评测和偏好进化提供了稳定底座。
