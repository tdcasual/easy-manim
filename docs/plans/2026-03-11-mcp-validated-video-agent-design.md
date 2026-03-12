# 原生 MCP 可验证视频 Agent 设计

## 1. 背景与目标
目标不是再做一个“输入 prompt，返回一段代码”的脚本工具，而是做一个**原生 MCP、面向 agent 调用、异步任务化、带自动验证闭环**的视频生成系统。它借鉴 `manim-generator` 最有价值的设计思路：
1. 用 Manim 代码作为中间表示，而不是让模型直接“幻想”视频。
2. 用真实渲染结果作为反馈，驱动自动修订。
3. 用日志、抽帧、评审和验证报告构成可复验闭环。

但本项目的目标形态与 `manim-generator` 不同：
1. 它不是单机 CLI 工作流，而是一个 **MCP Server**。
2. 它不是同步一次性返回，而是**先返回 `task_id`，后续轮询结果**。
3. 它不是只支持“重新生成”，而是支持**基于既有任务提出修改意见并持续修订**。
4. 它不是“渲染成功即完成”，而是**必须通过自动校验才算完成**。

成功标准：
1. Agent 可以通过 MCP 工具创建视频任务并拿到 `task_id`。
2. 系统能在后台完成生成、渲染、验证、必要时自动修订。
3. Agent 可以查询任务状态、验证报告、预览帧、脚本与最终视频。
4. Agent 可以在既有任务基础上给出修改意见，系统创建 revision 任务继续迭代。
5. 所有阶段均可追踪、可回放、可调试，不依赖模型的主观“我完成了”。

## 2. 产品形态与范围边界
本设计明确选择**研究型工具 / Research-grade MCP Service**，而不是 Web SaaS 或多人平台。

v1 形态：
1. MCP Server 暴露 tools 与 resources。
2. 本地或单机 worker 在后台推进任务状态机。
3. 任务结果以本地 artifacts + 结构化元数据形式保存。
4. 用户交互对象主要是 agent，而非普通终端用户界面。

v1 必保留：
1. 异步任务创建与轮询。
2. 真实 Manim 渲染。
3. 自动验证闭环。
4. revision lineage（基于既有任务继续修改）。
5. 视频、脚本、预览帧、验证报告可读取。

v1 明确不做：
1. 多人协作与权限系统。
2. 云对象存储与分布式队列。
3. 配音、字幕、配乐、素材库。
4. 富前端编辑器或浏览器端时间轴。
5. 多模型自动竞赛平台。

## 3. 核心设计原则
### 3.1 代码是中间表示，不是最终结果
用户需求先转成 Manim 代码，再通过真实渲染验证质量。这样系统面对的是“可执行工件”，不是不可验证的纯文本创意输出。

### 3.2 LLM 提建议，状态机做决策
模型负责生成代码、提出修复建议、进行高层评审；但任务是否完成、是否继续修订、是否失败，由状态机和验证规则决定，而不是由自然语言决定。

### 3.3 任务是第一公民
一次视频生成不是单个函数调用，而是一个可持续演化的任务对象。Agent 与系统协作的单位是 `VideoTask`，而不是“本次回复”。

### 3.4 所有结论必须有证据
每轮生成都要保留代码、日志、关键帧、验证报告、最终或中间视频。系统必须能解释“为什么通过”或“为什么失败”。

### 3.5 revision 不覆盖历史
任何显式修改意见都会创建新的子任务，保留 `parent_task_id` 与 lineage，允许回退、比较和审计。

## 4. 总体架构
推荐将系统拆成 8 个稳定模块：
1. `mcp_server`：暴露 tools / resources，不包含工作流业务。
2. `task_service`：创建任务、查询任务、创建 revision、取消任务。
3. `workflow_engine`：推进任务状态机。
4. `llm_adapter`：统一模型调用、provider 差异与 usage 收集。
5. `renderer`：执行 Manim、抽帧、收集渲染日志。
6. `validator`：硬校验、规则校验、LLM reviewer 校验。
7. `artifact_store`：保存脚本、视频、日志、关键帧、报告。
8. `task_store`：持久化任务、事件、artifact 索引与 validation 记录。

核心数据流：
`Agent -> MCP tools -> task_service -> task_store/job_queue -> workflow_engine -> llm_adapter/renderer/validator -> artifact_store/task_store -> MCP resources`

设计要点：
1. MCP 层只负责协议，不负责任务执行。
2. 工作流层不直接依赖具体存储细节，通过 repository/store 接口访问状态与 artifacts。
3. 渲染与验证要物理隔离于 MCP 请求线程，避免长任务阻塞交互。

## 5. MCP API 设计
### 5.1 Tools
v1 工具集固定为 5 个：
1. `create_video_task`
2. `get_video_task`
3. `revise_video_task`
4. `get_video_result`
5. `cancel_video_task`

### 5.2 `create_video_task`
输入建议：
1. `prompt`：视频目标描述。
2. `output_profile`：时长、分辨率、纵横比、质量配置。
3. `style_hints`：风格、节奏、镜头与布局偏好。
4. `validation_profile`：自动验证强度和阈值。
5. `max_revision_rounds`：自动修订上限。
6. `idempotency_key`：避免 agent 重试造成重复任务。

返回：
1. `task_id`
2. `status`
3. `poll_after_ms`
4. `resource_refs`

### 5.3 `get_video_task`
返回任务快照：
1. `task_id`
2. `status`：`queued | running | revising | completed | failed | cancelled`
3. `phase`：当前执行阶段
4. `attempt_count`
5. `parent_task_id`
6. `latest_validation_summary`
7. `artifact_summary`
8. `created_at / updated_at`

### 5.4 `revise_video_task`
输入：
1. `base_task_id`
2. `feedback`
3. `priority_constraints`
4. `preserve_working_parts`

行为：
1. 不覆盖原任务。
2. 创建新的 child task。
3. 继承原始需求、当前最佳脚本、验证报告与必要 artifacts。

### 5.5 `get_video_result`
仅在完成态返回：
1. `video_resource`
2. `preview_frame_resources`
3. `script_resource`
4. `validation_report_resource`
5. `summary`

### 5.6 Resources
推荐资源协议：
1. `video-task://{task_id}/task.json`
2. `video-task://{task_id}/validation_report.json`
3. `video-task://{task_id}/artifacts/current_script.py`
4. `video-task://{task_id}/artifacts/final_video.mp4`
5. `video-task://{task_id}/artifacts/previews/frame_001.png`

原则：tool 返回状态，resource 返回内容。

## 6. 任务模型与状态机
### 6.1 `VideoTask` 核心字段
建议最小字段：
1. `task_id`
2. `root_task_id`
3. `parent_task_id`
4. `status`
5. `phase`
6. `prompt`
7. `feedback`
8. `output_profile`
9. `validation_profile`
10. `attempt_count`
11. `current_script_artifact_id`
12. `best_result_artifact_id`
13. `created_at`
14. `updated_at`

### 6.2 状态机阶段
推荐流水线：
1. `queued`
2. `planning`
3. `generating_code`
4. `static_check`
5. `rendering`
6. `frame_extract`
7. `validation`
8. `revising`
9. `completed`
10. `failed`
11. `cancelled`

### 6.3 失败分流
1. 代码/渲染/验证错误：进入 `revising`，由系统构造 revision prompt 自动修订。
2. 环境错误（依赖缺失、权限不足、磁盘不足等）：进入 `failed`，避免模型无意义重试。
3. 超过最大修订轮数：进入 `failed`，但保留最佳候选结果和完整验证报告。

### 6.4 revision lineage
revision 规则：
1. `revise_video_task` 始终创建新任务。
2. 新任务继承父任务原始 prompt 和可复用 artifacts。
3. 每个任务都可追溯到 `root_task_id`。
4. 允许保留“当前最佳版本”，不要求每轮都覆盖旧结果。

## 7. Worker 执行管线
推荐单轮执行顺序：
1. `normalize_request`
2. `build_generation_prompt`
3. `generate_code`
4. `static_check`
5. `render`
6. `extract_frames`
7. `validate`
8. `decide_next_step`

### 7.1 `normalize_request`
将 prompt、风格、输出规格、修改意见整理成统一任务规范，减少 prompt builder 的分支复杂度。

### 7.2 `generate_code`
由 writer 模型输出完整 Manim 脚本。要求整份脚本可独立运行，不依赖任务外部未声明资源。

### 7.3 `static_check`
至少包含：
1. AST 可解析。
2. 依赖白名单。
3. 危险 API 拦截。
4. Scene 类提取。
5. 必要输出结构检查。

### 7.4 `render`
按 Scene 分开渲染，收集：
1. scene 级成功/失败信息
2. stdout/stderr
3. 视频文件路径
4. 运行时长与超时信息

### 7.5 `extract_frames`
从成功渲染的视频中抽取关键帧，作为预览和视觉验证输入。

### 7.6 `validate`
执行分层验证（见第 8 节）。

### 7.7 `decide_next_step`
读取结构化 `validation_report`：
1. 满足通过标准 -> `completed`
2. 可修复错误存在 -> `revising`
3. 不可恢复或达轮数上限 -> `failed`

## 8. 自动验证系统
验证必须分层，不允许只靠 reviewer 一段自然语言来决定通过与否。

### 8.1 硬校验（Hard Validation）
最基础且必须通过：
1. 脚本可解析。
2. Manim 成功渲染至少目标 scene。
3. 输出视频存在且可探测。
4. 视频分辨率、时长、scene 数等满足基本配置。

### 8.2 规则校验（Rule-based Validation）
尽量程序化完成：
1. 黑屏或空白帧检测。
2. 明显越界/大面积裁切检测。
3. 末尾长时间静止或卡住检测。
4. 标题/文本重叠的简单启发式检测。
5. 视频文件损坏与编码异常检测。

### 8.3 LLM Reviewer 校验
输入：需求、当前代码、渲染日志、关键帧、上轮验证摘要。
输出建议强制结构化：
1. `pass / fail`
2. `critical_issues`
3. `suggested_changes`
4. `confidence`
5. `semantic_alignment_summary`

### 8.4 通过标准
只有同时满足以下条件才标记为 `completed`：
1. 硬校验全部通过。
2. 无 critical issue。
3. 规则错误数不超过阈值。
4. LLM reviewer 未要求继续修订。

## 9. 错误处理与安全边界
该系统本质上会执行 LLM 生成的代码，因此必须默认代码不可信。

### 9.1 静态限制
至少禁止：
1. `subprocess`
2. `socket`
3. `requests` 或任意网络访问
4. `eval/exec`
5. 非白名单路径写入
6. 动态 import 任意模块

### 9.2 受限执行环境
渲染进程建议：
1. 使用独立工作目录。
2. 设置 CPU / 内存 / 时间上限。
3. 不允许访问任务外部敏感路径。
4. 与 MCP 主进程解耦。

### 9.3 错误对象标准化
统一错误对象至少包含：
1. `error_type`：`generation | static_check | render | validation | infra | cancelled`
2. `retryable`
3. `failure_summary`
4. `raw_logs_ref`
5. `suggested_revision_focus`

### 9.4 状态机决策优先于模型说法
即使模型说“已完成”，只要验证未通过，系统仍应继续修订或失败退出。

## 10. 数据存储与目录结构
v1 推荐：**SQLite + 本地文件系统 artifacts**。

### 10.1 数据库存储
推荐 4 张主表：
1. `video_tasks`
2. `task_events`
3. `task_artifacts`
4. `task_validations`

用途：
1. `video_tasks`：任务主对象与当前状态。
2. `task_events`：时间线事件与状态迁移。
3. `task_artifacts`：文件型结果索引。
4. `task_validations`：每轮验证结果。

### 10.2 文件目录
建议目录：
```text
data/
  tasks/
    <task_id>/
      task.json
      logs/
        render.log
        worker.log
      artifacts/
        current_script.py
        final_video.mp4
        previews/
          frame_001.png
      validations/
        validation_report_v1.json
        validation_report_v2.json
```

原则：
1. 结构化元数据进数据库。
2. 大文件与中间产物进文件系统。
3. 任何 artifact 都必须能通过 `task_artifacts` 找回。

## 11. 推荐技术栈
v1 推荐全 Python 实现：
1. `Python 3.11+`
2. `MCP Python SDK`
3. `Pydantic`：tool I/O、任务对象、validation report
4. `SQLite`：任务状态与索引
5. `subprocess`：受限调用 Manim
6. `ffmpeg / ffprobe + OpenCV`：视频探测、抽帧、基础规则校验
7. `Rich`：本地开发调试输出（非核心依赖）

明确不推荐 v1 采用双栈：
1. 不要 `Node 做 MCP + Python 做渲染`。
2. 不要上 Redis / Celery / Postgres / S3，除非已有明显单机瓶颈。

## 12. 推荐代码目录
```text
src/
  video_agent/
    server/
      mcp_tools.py
      mcp_resources.py
    application/
      task_service.py
      revision_service.py
      workflow_engine.py
    domain/
      models.py
      enums.py
      validation_models.py
    adapters/
      llm/
        client.py
        prompt_builder.py
      rendering/
        manim_runner.py
        frame_extractor.py
      storage/
        sqlite_store.py
        artifact_store.py
    validation/
      static_check.py
      hard_validation.py
      rule_validation.py
      reviewer_validation.py
    worker/
      worker_loop.py
tests/
  unit/
  integration/
  e2e/
```

拆分原则：
1. `server` 只管 MCP 协议。
2. `application` 只编排业务流程。
3. `domain` 不依赖具体框架。
4. `adapters` 负责和外部系统交互。
5. `validation` 不嵌进 renderer 或 server，保持独立演进能力。

## 13. 分阶段落地建议
### 阶段 1：最小任务闭环
1. 搭 MCP server。
2. 完成 `create_video_task / get_video_task / get_video_result`。
3. 打通单轮生成 -> 渲染 -> 硬校验 -> 返回结果。

### 阶段 2：验证闭环
1. 加入抽帧与规则校验。
2. 引入 reviewer 校验。
3. 引入自动 revision。

### 阶段 3：可持续修订
1. 实现 `revise_video_task`。
2. 加入 parent/root lineage。
3. 保存最佳候选与 revision 历史。

### 阶段 4：稳健性与可观测性
1. 完善错误模型。
2. 增加取消任务。
3. 增加审计日志、usage 与成本汇总。
4. 增加 e2e 测试与故障注入测试。

## 14. 风险与控制
主要风险：
1. LLM 生成代码不可控，导致执行风险高。
2. 渲染耗时长，任务积压影响反馈速度。
3. 纯 LLM reviewer 容易产生不稳定结论。
4. revision 轮数过多导致成本失控。

控制手段：
1. 先做严格静态检查与执行限制。
2. worker 与 MCP 线程解耦，任务可轮询。
3. reviewer 结论必须结构化，并由状态机仲裁。
4. 限制自动修订轮数，并保留最佳候选结果。
5. 从 v1 开始记录 token、耗时、每阶段失败原因。

## 15. 进入实现前的冻结决策
在开始编码前，应冻结以下决策：
1. 单机架构：SQLite + 本地文件系统。
2. 单语言：Python。
3. 单渲染后端：Manim。
4. 异步任务模型：先 `task_id`，后轮询结果。
5. revision 语义：新建 child task，不覆盖原任务。
6. 完成定义：必须通过自动验证，而非仅渲染成功。

以上冻结点的作用，是保证 v1 把真正关键的“可验证闭环 + 可修订任务对象”做扎实，而不是提前滑向平台化复杂度。
