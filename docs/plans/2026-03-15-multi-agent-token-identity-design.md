# 多 Agent Token 身份隔离与偏好分层设计

## 1. 目标
当前 `easy-manim` 已经具备面向 agent 调用的视频生成、校验、自动修复与 revision 能力，但它仍然是“单一调用面”的系统：任何调用方都共享同一套默认行为、同一批任务视图与同一组资源读取路径。

本设计的目标不是把项目升级成完整 SaaS 平台，而是补上一个对 agent 调用场景最关键的薄层：

1. 多个上层 agent 可以通过 token 进入同一个 MCP 服务。
2. 每个 agent 拥有独立身份、独立默认偏好、独立任务视图。
3. 任务创建时自动注入该 agent 的默认 `style_hints`、`output_profile`、`validation_profile`。
4. 不同 agent 之间不能互相读取对方的任务、结果和 artifacts。
5. 当前已经存在的工作流内核尽量少改，重点在入口鉴权、偏好解析与访问隔离。

## 2. 非目标
第一版明确不做以下能力：

1. 长期会话记忆与自动偏好学习。
2. 多租户计费、配额和账单系统。
3. Web 控制台或人工用户登录界面。
4. 云端对象存储和分布式队列。
5. 基于 token 的复杂 RBAC 权限树。

第一版只解决“多个 agent 用 token 做身份隔离和偏好区分”。

## 3. 推荐方案
推荐采用三层分离模型，而不是把 token 直接当成配置容器：

1. `Agent Profile`
   负责存放长期稳定的默认偏好与平台策略。
2. `Agent Token`
   负责身份认证、停用、轮换与少量临时 override。
3. `Effective Request Config`
   负责把系统默认值、profile 偏好、token override 与请求级显式参数合并成当前任务真正执行的配置。

这样设计的优点是：

1. token 可以轮换，不影响 agent 的长期偏好。
2. 同一个 agent 可以持有多个 token，用于不同环境或 scope。
3. 偏好与认证解耦，后续加 session memory 时不会推翻第一版模型。

## 4. 传输与认证策略
理想状态下，HTTP transport 可以直接从 `Authorization: Bearer <token>` 里取 token。但当前本地 `FastMCP` 工具层默认暴露的是 `Context`、`request_id`、`client_id` 与 `meta`，并不保证在所有 transport 下都能稳定读取原始请求头。

因此第一版推荐采用一个**传输兼容的会话引导方案**：

1. 新增 `authenticate_agent(agent_token)` 工具。
2. 客户端在 MCP 连接建立后先调用该工具。
3. 服务端把“当前 MCP 会话 -> agent principal”记录到内存中的 session auth registry。
4. 后续 `create_video_task`、`revise_video_task`、`get_video_task`、`get_video_result` 以及资源读取，都从当前会话拿 agent principal，而不是要求每个 tool 都重复传 token。

补充策略：

1. `auth_mode=disabled`
   默认开发模式。不要求鉴权，所有请求走本地匿名 profile。
2. `auth_mode=required`
   多 agent 模式。所有 task tools 和 task resources 都必须先完成 `authenticate_agent(...)`。

如果后续确认某个 transport 能稳定读取原始 header，可以把 header token 解析做成 `authenticate_agent(...)` 之前的一层适配器，但不应影响下游设计。

## 5. 数据模型
第一版建议新增两张主表，并给任务表加一个归属列。

### 5.1 `agent_profiles`
建议字段：

1. `agent_id`
2. `name`
3. `status`
4. `profile_json`
5. `policy_json`
6. `created_at`
7. `updated_at`

其中：

1. `profile_json`
   存默认 `style_hints`、`output_profile`、`validation_profile`
2. `policy_json`
   存平台侧偏好，例如默认是否允许 auto-repair、默认质量级别、允许的 scope

### 5.2 `agent_tokens`
建议字段：

1. `token_hash`
2. `agent_id`
3. `status`
4. `scopes_json`
5. `override_json`
6. `last_seen_at`
7. `created_at`

注意：

1. 数据库只存 `token_hash`，不存明文 token。
2. `override_json` 只用于小范围覆盖，不取代 profile。

### 5.3 `video_tasks`
建议在现有表上新增：

1. `agent_id`

并在 `task_json` 中扩展：

1. `agent_id`
2. `profile_version`
3. `effective_profile_digest`
4. `effective_request_profile`

这样既能高效按 agent 过滤任务，也能完整回放某个任务当时到底用了什么偏好配置。

## 6. 偏好解析顺序
第一版固定采用以下优先级：

`system defaults -> agent profile -> token override -> request override`

解释：

1. 系统默认值来自 `Settings` 和内建默认策略。
2. `agent profile` 代表该 agent 的长期稳定偏好。
3. `token override` 代表某个 token 的临时用途差异，例如“这个 token 总是 production 质量”。
4. `request override` 只影响当前任务，是最高优先级。

解析产物建议命名为 `EffectiveRequestConfig`，其中至少包含：

1. `style_hints`
2. `output_profile`
3. `validation_profile`
4. `policy_flags`
5. `profile_digest`

## 7. 任务与修订行为
一旦请求通过身份校验，任务层尽量保持现有行为不变。

新增要求：

1. `create_video_task(...)` 创建的任务必须带 `agent_id`。
2. `revise_video_task(...)`、`retry_video_task(...)`、`create_auto_repair_task(...)` 必须继承父任务的 `agent_id` 与 `effective_request_profile`。
3. `list_video_tasks(...)` 默认只返回当前 agent 的任务。
4. `get_video_task(...)` 与 `get_video_result(...)` 只能读取当前 agent 自己的任务。

这样一来，系统仍然是“任务驱动”的视频执行器，但任务已经具备清晰的 agent 归属。

## 8. 资源隔离
当前资源路径采用 `video-task://{task_id}/...`，如果不加隔离，不同 agent 只要知道对方的 `task_id`，理论上就有可能读取资源。

第一版要求：

1. 所有 task resource 读取都必须通过“当前会话已认证的 agent principal”校验。
2. 校验规则很简单：`task.agent_id == current_agent_id`。
3. 若不匹配，直接拒绝读取，不返回 task failure，不写入任务数据库。

因此资源层需要从“只校验路径安全”升级为“路径安全 + 归属安全”。

## 9. 错误模型
身份层错误与视频生成错误必须分层。

### 9.1 身份层错误
建议新增错误码：

1. `agent_token_missing`
2. `agent_token_invalid`
3. `agent_token_disabled`
4. `agent_scope_denied`
5. `agent_not_authenticated`
6. `agent_resource_forbidden`

这些错误：

1. 不创建任务。
2. 不写任务失败 artifact。
3. 直接作为 MCP tool / resource 访问错误返回。

### 9.2 工作流错误
现有 `failure_contract` 继续只负责工作流内部失败，例如：

1. `render_failed`
2. `provider_auth_error`
3. `near_blank_preview`
4. `unsafe_*`

身份问题不进入 `failure_contract`。

## 10. 配置与运行模式
建议在 `Settings` 中新增：

1. `auth_mode: disabled | required`
2. `anonymous_agent_id`
3. `anonymous_profile_json`

默认：

1. 开发环境 `auth_mode=disabled`
2. 多 agent 生产或集成环境 `auth_mode=required`

这样不会打断当前本地调试体验，也能平滑切到多 agent 运行模式。

## 11. 管理平面
第一版不建议先开放 MCP 管理工具，而是先补一个本地 CLI：

1. `easy-manim-agent-admin create-profile`
2. `easy-manim-agent-admin issue-token`
3. `easy-manim-agent-admin disable-token`
4. `easy-manim-agent-admin inspect-profile`

原因：

1. 创作平面与管理平面分离更安全。
2. CLI 更容易被运维脚本或本地开发环境使用。
3. 先把底层身份模型做稳，再考虑是否把这些管理能力暴露为 MCP tool。

## 12. 分阶段实施
推荐拆成三个阶段。

### Phase 1：身份隔离与偏好注入
目标：

1. token 能映射到 agent profile
2. 任务能带 `agent_id`
3. profile 默认值能注入任务
4. 不同 agent 不能互读任务与 resources

### Phase 2：会话记忆
目标：

1. 增加 `session_id`
2. 支持短期偏好记忆
3. revision 自动挂到同一 session

### Phase 3：偏好进化与 agent-aware eval
目标：

1. 从 session 中提炼长期偏好
2. 增加 `promote_session_preferences`
3. 做不同 agent profile 的回归评测

## 13. 推荐结论
对于当前项目，最合适的下一步不是直接做完整多租户平台，而是先补一个“轻但正确”的 `token -> agent profile -> effective request config` 身份层。

这样做的收益最大：

1. 立刻满足“多个 agent 用 token 隔离与区分偏好”的核心诉求。
2. 不会重写既有工作流内核。
3. 为未来的 session memory 和持续进化留足结构空间。
