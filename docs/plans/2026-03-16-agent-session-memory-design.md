# Agent Session Memory 设计

## 1. 目标
在已经完成的多 agent token 身份隔离之上，为 `easy-manim` 增加一个真正面向 agent 调用场景的“短期会话记忆层”：

1. 记忆严格绑定到**当前 live MCP 会话**，而不是绑定到 `agent_id`。
2. 记忆只保存**任务与产物摘要**，不保存原始对话日志。
3. 记忆默认只在**revise / retry / auto-repair** 这三条迭代链路里自动参与提示构建。
4. 首次 `create_video_task(...)` 保持干净，不自动注入历史记忆。
5. 记忆必须可以被 tool 读取、摘要化、清空。
6. 当前版本只做 **session-only memory**，但要预留一个稳定的导出摘要接口，供未来跨 session 持久记忆复用。

## 2. 已确认约束
本阶段已经明确的产品约束如下：

1. 同一个 `agent_id` 在两个并发 MCP 会话中**不能共享**记忆。
2. 记忆内容以“任务目标、修订反馈、关键失败/成功结果、关键 artifacts 引用”为主。
3. 不把完整 prompt history、完整 stderr、完整对话 transcript 塞进 memory。
4. 读取空 memory 不报错，而是返回稳定的空结构。
5. 清空 memory 只影响当前 session 的内存态，不回写历史任务和 artifacts。
6. 如果服务重启导致 session memory 丢失，后续迭代任务仍然应该继续工作，只是拿到空 memory。

## 3. 关键设计判断
这次设计里最重要的判断不是“要不要做一个 in-memory dict”，而是：

**后台 auto-repair 没有 live MCP 上下文，但它又必须沿着原 session 的短期记忆继续演化。**

如果只用 `agent_id` 关联 memory，那么同一个 agent 的多个并发会话会错误共享记忆；如果只用当前请求里的 `session_key`，后台 auto-repair 又拿不到这个 live 上下文。

因此本阶段应该正式引入一个稳定的 `session_id`：

1. `session_key`
   是 transport / FastMCP 层当前连接的临时键，用于定位当前 live 会话。
2. `session_id`
   是服务端为该 live 会话分配的稳定标识，用于任务 lineage 和 session memory 绑定。

`session_key -> session_id` 的映射只存在内存中；`session_id` 则会跟着任务一起持久化，使后台 auto-repair 能继续沿用原会话的 memory。

## 4. 推荐架构

### 4.1 SessionMemoryRegistry
新增一个与 `SessionAuthRegistry` 并列的内存层组件，例如 `SessionMemoryRegistry`，负责两类状态：

1. `session_key -> session_id`
2. `session_id -> SessionMemoryState`

推荐它保持非常轻量：

1. 不存完整 artifacts 内容。
2. 不存完整任务快照副本。
3. 只存 session 级别的 task references、简短摘要和时间顺序。

这样可以保持：

1. 与当前 `SessionAuthRegistry` 一样的轻量部署模型。
2. 未来可替换为 persistent store，而不反过来污染当前工作流核心。

### 4.2 SessionMemoryState
每个 `session_id` 下维护一个稳定的只读视图状态，建议至少包含：

1. `session_id`
2. `agent_id`
3. `created_at`
4. `updated_at`
5. `entries`

其中 `entries` 推荐按 **root task lineage** 聚合，而不是简单平铺每个 task。原因：

1. revise / retry / auto-repair 天然围绕同一 `root_task_id` 演化。
2. 面向 agent 的“记忆”更关心一条任务线发生了什么，而不是一串离散 task id。
3. 后续做 persistent summary 时，lineage 级摘要更容易提炼出“目标 -> 尝试 -> 结果”的结构。

### 4.3 SessionMemoryEntry
建议每个 entry 代表一条任务演化线，核心字段可以是：

1. `root_task_id`
2. `latest_task_id`
3. `task_goal_summary`
4. `latest_status`
5. `latest_result_summary`
6. `attempts`
7. `artifact_refs`
8. `updated_at`

`attempts` 中只保留有限窗口，例如最近 3 次尝试，每次尝试只保留：

1. `task_id`
2. `attempt_kind`：`create | revise | retry | auto_repair`
3. `feedback_summary`
4. `status`
5. `result_summary`
6. `artifact_refs`
7. `created_at`

## 5. 存储与数据边界

### 5.1 `VideoTask` 新增字段
为了让后台 auto-repair 能继续拿到原 session 的 memory，本阶段建议给 `VideoTask` 增加：

1. `session_id: str | None`
2. `memory_context_summary: str | None`
3. `memory_context_digest: str | None`

含义如下：

1. `session_id`
   表示该任务所属的 live session 记忆作用域。
2. `memory_context_summary`
   表示该任务在创建时实际注入到 prompt 的 session memory 摘要文本。
3. `memory_context_digest`
   表示该摘要的稳定摘要指纹，便于后续调试、去重和回放。

这里要注意：

1. 初次 `create_video_task(...)` 创建的任务，`memory_context_summary` 应为空。
2. revise / retry / auto-repair 创建的 child task 才会携带 `memory_context_summary`。
3. `session_id` 需要在 revision lineage 中继承。

### 5.2 数据库存储
推荐在 `video_tasks` 表上新增：

1. `session_id`

同时把 `memory_context_summary` / `memory_context_digest` 保存在 `task_json` 中即可，除非后续发现有独立查询需求再上列。

原因：

1. `session_id` 需要被快速读取，用于后台 auto-repair 和后续调试。
2. `memory_context_summary` 更多是“任务创建时的上下文快照”，不属于高频筛选字段。

## 6. 记忆内容如何生成
本阶段不建议引入新的 LLM summarizer，而是采用**确定性结构化摘要**：

1. 任务目标来自 `prompt` 的压缩文本。
2. 修订背景来自 `feedback` 的压缩文本。
3. 结果摘要来自：
   - `status`
   - `latest_validation.summary`
   - 首个 failure issue code
   - auto-repair decision 摘要
4. artifacts 只保留对 agent 真正有帮助的稳定引用，例如：
   - `video-task://{task_id}/task.json`
   - `video-task://{task_id}/artifacts/current_script.py`
   - `video-task://{task_id}/artifacts/final_video.mp4`
   - `video-task://{task_id}/artifacts/failure_contract.json`
   - `video-task://{task_id}/validations/<report>.json`

这能带来几个好处：

1. 没有额外模型成本。
2. 结果可预测、可测试。
3. 后续 persistent memory 可以直接复用这套规范化结构，而不是从自由文本里二次解析。

## 7. 生命周期与接线方式

### 7.1 会话建立
当 MCP session 第一次进入需要 memory 的路径时，服务端应：

1. 根据当前 `session_key` 调用 `SessionMemoryRegistry.ensure_session(...)`
2. 获取或分配稳定的 `session_id`
3. 将该 `session_id` 用于当前请求以及后续任务创建

如果 `auth_mode=required`，则仍然以已认证 agent 为主；memory 只是在此之上附加 `session_id`。

### 7.2 首次创建任务
`create_video_task(...)` 的行为应是：

1. 仍然**不注入**已有 memory 到生成 prompt。
2. 创建的新 root task 带上 `session_id`。
3. 任务创建成功后，把该 root task 记录进当前 session memory。

这样首轮创作保持干净，但从第一轮开始就留下后续迭代可读的 session context。

### 7.3 revise / retry
`revise_video_task(...)` 和 `retry_video_task(...)` 的行为应是：

1. 从父任务拿到 `session_id`
2. 基于该 `session_id` 读取当前 session memory 摘要
3. 将摘要写入 child task 的 `memory_context_summary`
4. child task 继承相同 `session_id`
5. child task 创建后再回写到该 session 的 memory entry

### 7.4 auto-repair
`auto_repair` 必须沿着父任务的 `session_id` 继续工作：

1. 失败父任务上必须能读到 `session_id`
2. `AutoRepairService` 在生成 targeted repair feedback 时读取对应 `session_id` 的 memory summary
3. 自动修复 child task 继承该 `session_id`
4. 如果 registry 里已经没有这个 session 的 memory state，则退化为“空记忆 auto-repair”，但不能报错

这保证 auto-repair 仍然符合“严格按 session 隔离”的原则，而不是错误地退回 `agent_id` 共享模型。

## 8. Tool 设计
建议新增三个 MCP tools：

1. `get_session_memory()`
2. `summarize_session_memory()`
3. `clear_session_memory()`

### 8.1 `get_session_memory()`
返回当前 session 的可读详情，建议结构包含：

1. `session_id`
2. `agent_id`
3. `entry_count`
4. `entries`
5. `updated_at`

空 memory 时返回：

1. `entry_count = 0`
2. `entries = []`
3. `summary_text = ""` 或 `None`
4. 不抛异常

### 8.2 `summarize_session_memory()`
返回当前 session 的规范化摘要接口，重点不是“给人读得很长”，而是给未来 persistent memory 使用：

1. `session_id`
2. `summary_text`
3. `summary_digest`
4. `entry_count`
5. `lineage_refs`

未来如果要做跨 session memory，只需要把这个 summary payload 提升到 profile 或外部 store，而不必重写 session memory 核心。

### 8.3 `clear_session_memory()`
只清空当前 `session_id` 对应的 memory state，返回：

1. `session_id`
2. `cleared_entry_count`
3. `cleared_attempt_count`
4. `cleared: true`

它不做以下事情：

1. 不删数据库任务
2. 不删 artifacts
3. 不影响其他 session
4. 不影响同一个 agent 的其他 live session

## 9. Prompt 接入策略

### 9.1 生成 prompt
`build_generation_prompt(...)` 增加可选参数：

1. `memory_context_summary: str | None`

只有在 child task 的 `memory_context_summary` 非空时才注入，例如：

1. `Session memory context: ...`
2. `Reuse what already worked; avoid repeating recent failures.`

### 9.2 auto-repair feedback
`build_targeted_repair_feedback(...)` 也应支持可选的 `memory_context_summary`，用于告诉模型：

1. 哪些思路在本 session 里已经试过
2. 哪些 artifacts 已经可复用
3. 这次修复应该避免重复踩坑

### 9.3 首次 create 保持干净
首次 root task 不传 `memory_context_summary`，这样不会让第一次创作被之前 session 的失败历史“污染”。

## 10. 错误模型
session memory 相关错误应尽量设计成**低干扰**：

1. `get_session_memory()` 对空 session 返回空结构，不报错。
2. `clear_session_memory()` 对空 session 返回 `cleared_entry_count=0`。
3. `summarize_session_memory()` 对空 session 返回空摘要和稳定 digest/null。
4. revise / retry / auto-repair 读不到 memory 时，直接按空摘要继续，而不是阻断任务创建。

只有真正的参数错误或内部编码错误才应该抛出 tool failure。

## 11. 测试策略
建议测试分三层：

### 11.1 单元测试
覆盖：

1. `SessionMemoryRegistry` 的 session_id 分配与严格隔离
2. 空 memory 的稳定结构
3. clear 行为只影响当前 session
4. summary digest 的稳定性

### 11.2 应用层/集成测试
覆盖：

1. `create_video_task(...)` 记录 root task，但不注入 memory context
2. `revise_video_task(...)` 注入 memory context 并继承 `session_id`
3. `retry_video_task(...)` 注入 memory context
4. `auto_repair` 在后台仍然沿用父任务 `session_id`
5. 同一个 `agent_id` 的两个 session 拥有不同 memory

### 11.3 FastMCP 集成测试
覆盖：

1. 新 tools 已注册
2. 两个 session 分别认证同一 agent token 后，memory 互不可见
3. `clear_session_memory()` 只清空调用方当前 session

## 12. 推荐实施顺序
推荐按以下顺序推进：

1. 先补 `session_id` + `SessionMemoryRegistry`
2. 再把 `TaskService / AutoRepairService` 接到 `session_id`
3. 再开放 `get/summarize/clear_session_memory`
4. 最后把 prompt builder 与 targeted repair feedback 接上 memory context

这样可以先把隔离边界做对，再把 memory 真正送进迭代提示里。

## 13. 结论
当前项目最适合的 session memory 方案，不是上来就做数据库型长期记忆，而是在现有 `SessionAuthRegistry + TaskService + revision/repair lineage` 之上，加一层**严格按 live session 隔离、任务级可回放、后台 auto-repair 可继承、未来可导出持久摘要**的短期记忆层。

这条路径最符合现在系统的 agent-first 定位，也不会推翻前一阶段已经完成的 token identity 架构。
