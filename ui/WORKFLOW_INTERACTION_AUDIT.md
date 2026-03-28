# 🔄 Studio 工作流与交互逻辑审计报告

**审计日期**: 2026-03-27  
**审计范围**: 用户工作流、状态流转、交互逻辑、边界情况  

---

## 📊 总体评分

```
工作流设计: 7.5/10
交互逻辑: 7.0/10
状态管理: 7.5/10
边界处理: 6.0/10
----------------
综合评分: 7.0/10
```

---

## 1️⃣ 用户工作流分析

### 核心工作流

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  输入提示词  │ → │  点击生成   │ → │  等待生成   │ → │  查看结果   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ • 快捷提示  │    │ • 创建任务  │    │ • 轮询状态  │    │ • 视频展示  │
│ • 参数设置  │    │ • 清空输入  │    │ • 进度反馈  │    │ • 历史记录  │
│ • 键盘输入  │    │ • 错误处理  │    │ • 取消机制  │    │ • 全屏播放  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

### 工作流步骤详细分析

#### 步骤 1: 输入提示词

**当前实现**:
```typescript
// ChatInput.tsx
const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
  onChange(e.target.value);  // 直接透传
};

// Studio.tsx
const [prompt, setPrompt] = useState("");
```

**评分**: 7/10

**优点** ✅:
- 实时输入反馈
- 自动调整高度
- 支持多行（Shift+Enter）
- Enter 快速提交

**问题** ⚠️:
1. **无输入防抖** - 每输入一个字符都触发渲染
2. **无输入统计** - 用户不知道已输入多少字
3. **无提示词验证** - 空内容/过长内容无前置提示

**建议改进**:
```typescript
// 添加输入统计和验证
const [charCount, setCharCount] = useState(0);
const isValid = prompt.trim().length > 0 && prompt.length <= 500;

// 显示字数统计
<div className="char-count">{charCount}/500</div>
```

---

#### 步骤 2: 提交生成

**当前实现**:
```typescript
// Studio.tsx:295-320
const handleSubmit = useCallback(async () => {
  if (!sessionToken || !prompt.trim() || isGenerating) return;

  setIsGenerating(true);
  setError(null);
  
  try {
    const result = await createTask(prompt.trim(), sessionToken);
    
    if (result?.task_id) {
      setCurrentTask({
        id: result.task_id,
        title: result.display_title || prompt.trim(),
        status: "queued",
      });
      setPrompt("");  // 清空输入
      
      const cleanup = pollTaskStatus(result.task_id);
      pollCleanupRef.current = cleanup;
    }
  } catch (err) {
    setError(parseError(err));
    setIsGenerating(false);
  }
}, [sessionToken, prompt, isGenerating]);
```

**评分**: 7.5/10

**优点** ✅:
- 前置条件检查完整（登录/非空/非生成中）
- 立即清空输入，体验流畅
- 错误处理完善
- 启动轮询获取状态

**问题** ⚠️:
1. **参数未传递** - generationParams 设置但未传给 API
   ```typescript
   // 当前只传了 prompt
   createTask(prompt.trim(), sessionToken)
   
   // 应该传递参数
   createTask({ 
     prompt: prompt.trim(), 
     ...generationParams 
   }, sessionToken)
   ```

2. **无提交确认** - 点击后立即提交，无二次确认
3. **提交后无视觉反馈** - 除了清空输入，按钮状态变化滞后

---

#### 步骤 3: 生成过程

**当前实现**:
```typescript
// Studio.tsx:323-401 - 智能轮询
const pollTaskStatus = useCallback((taskId: string) => {
  // 智能轮询间隔
  const getPollInterval = (status: string, hasError: boolean) => {
    if (hasError) return Math.min(30000, 1000 * Math.pow(2, errorAttempt));
    if (status === "queued") return 5000;
    if (status === "running") return 3000;
    return 3000;
  };
  
  // 轮询逻辑...
}, []);
```

**评分**: 8/10

**优点** ✅:
- 智能轮询（排队5s/运行3s）
- 指数退避错误处理
- 可取消的轮询机制
- 进度条动画反馈

**问题** ⚠️:
1. **无主动取消** - 用户无法主动取消生成
   ```typescript
   // 需要添加
   const handleCancel = () => {
     pollCleanupRef.current?.();
     cancelTask(taskId, sessionToken);
     setIsGenerating(false);
   };
   ```

2. **无暂停/恢复** - 长时间生成不能暂停

---

#### 步骤 4: 查看结果

**当前实现**:
```typescript
// VideoStage.tsx 展示视频
// Studio.tsx:404-415 选择历史
const handleSelectHistory = useCallback((id: string) => {
  const video = videos.find((v) => v.task_id === id);
  if (video) {
    setCurrentTask({
      id: video.task_id,
      videoUrl: video.latest_video_url,
      title: video.display_title || video.task_id,
      status: video.status,
    });
  }
  setIsHistoryOpen(false);
}, [videos]);
```

**评分**: 7/10

**优点** ✅:
- 视频播放控制完整
- 全屏功能
- 历史切换流畅

**问题** ⚠️:
1. **无结果对比** - 无法对比多个生成结果
2. **无结果操作** - 不能删除/重命名/收藏单个视频
3. **下载功能缺失** - 只能播放，不能直接下载

---

## 2️⃣ 状态流转分析

### 状态机图

```
                    ┌─────────────┐
         ┌─────────│    Idle     │◄────────────────┐
         │         │  (等待输入)  │                 │
         │         └──────┬──────┘                 │
         │                │ 提交                   │
         │                ▼                        │
         │         ┌─────────────┐    失败         │
         │    ┌───►│   Queued    │─────────────────┤
         │    │    │   (排队中)   │                 │
         │    │    └──────┬──────┘                 │
         │    │           │ 开始运行               │
         │    │           ▼                        │
         │    │    ┌─────────────┐    失败         │
         │    └───►│   Running   │─────────────────┤
         │         │   (生成中)   │                 │
         │         └──────┬──────┘                 │
         │                │ 完成                   │
         │                ▼                        │
         │         ┌─────────────┐                │
         └────────►│  Completed  │────────────────┘
                   │   (已完成)   │
                   └─────────────┘
```

### 状态流转表

| 当前状态 | 事件 | 下一状态 | 处理 | 评分 |
|---------|------|---------|------|------|
| Idle | 点击生成 | Queued | 创建任务、清空输入、启动轮询 | ✅ 8/10 |
| Queued | 状态更新 | Running | 更新状态、继续轮询 | ✅ 8/10 |
| Queued | 失败 | Idle | 显示错误、停止轮询 | ✅ 7/10 |
| Running | 状态更新 | Completed | 更新视频、停止轮询、刷新历史 | ✅ 8/10 |
| Running | 失败 | Idle | 显示错误、停止轮询 | ✅ 7/10 |
| Completed | 选择其他 | Completed | 切换显示 | ✅ 7/10 |

**缺失的流转** ❌:
- Running → Cancelled（用户主动取消）
- Completed → Deleted（删除结果）
- Any → Retrying（重试机制）

---

## 3️⃣ 交互逻辑问题

### 问题 1: 参数设置与工作流脱节

**现状**: SettingsPanel 设置参数，但提交时未使用

```typescript
// Studio.tsx:157
const [generationParams, setGenerationParams] = useState<GenerationParams>(defaultParams);

// 但提交时只传了 prompt
const result = await createTask(prompt.trim(), sessionToken);
```

**影响**: 用户设置分辨率/时长/风格后，实际生成仍用默认参数

**建议**:
```typescript
// 修改 API 调用
type CreateTaskRequest = {
  prompt: string;
  resolution?: string;
  duration?: string;
  style?: string;
  quality?: string;
};

const result = await createTask({
  prompt: prompt.trim(),
  ...generationParams,
}, sessionToken);
```

---

### 问题 2: 快捷提示交互不完整

**现状**:
```typescript
const handleQuickPrompt = (prompt: string) => {
  onQuickPromptClick?.(prompt);  // 只回调
  textareaRef.current?.focus();  // 只聚焦
};

// Studio.tsx 回调
onQuickPromptClick={(text) => {
  setPrompt((prev) => (prev ? prev + " " + text : text));
}}
```

**问题**:
1. 追加模式（prev + text）可能不符合用户预期
2. 无提示说明当前是追加还是替换
3. 点击后光标位置不确定

**建议**:
```typescript
// 提供两种模式
const handleQuickPrompt = (prompt: string, mode: 'append' | 'replace') => {
  if (mode === 'replace') {
    onChange(prompt);
  } else {
    onChange(prev ? `${prev}, ${prompt}` : prompt);
  }
  // 聚焦到末尾
  setTimeout(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.selectionStart = textarea.value.length;
      textarea.selectionEnd = textarea.value.length;
    }
  }, 0);
};
```

---

### 问题 3: 错误恢复流程不完整

**现状**:
```typescript
catch (err) {
  setError(parseError(err));
  setIsGenerating(false);
}
```

**问题**:
1. 重试按钮只是清空错误，没有实际重试逻辑
2. 任务失败后无法一键重试
3. 无错误日志导出/反馈入口

**建议**:
```typescript
// 添加重试逻辑
const handleRetry = () => {
  if (currentTask?.status === "failed") {
    retryTask(currentTask.id, sessionToken).then(() => {
      setIsGenerating(true);
      pollTaskStatus(currentTask.id);
    });
  } else {
    // 重新提交
    handleSubmit();
  }
};
```

---

### 问题 4: 并发控制缺失

**现状**: 无全局生成状态锁

```typescript
// 用户可能同时触发多个生成
const handleSubmit = useCallback(async () => {
  if (!sessionToken || !prompt.trim() || isGenerating) return;  // 仅依赖 isGenerating
  // ...
}, [sessionToken, prompt, isGenerating]);
```

**问题**:
1. 快速双击可能提交两次
2. 切换历史时如果正在生成，状态可能混乱

**建议**:
```typescript
// 添加提交锁
const submitLockRef = useRef(false);

const handleSubmit = useCallback(async () => {
  if (submitLockRef.current) return;
  submitLockRef.current = true;
  
  try {
    // ... 提交逻辑
  } finally {
    submitLockRef.current = false;
  }
}, []);
```

---

## 4️⃣ 边界情况检查

| 场景 | 当前行为 | 期望行为 | 状态 |
|------|---------|---------|------|
| 未登录 | 重定向到登录页 | ✅ 正确 | ✅ |
| 网络断开 | 显示网络错误，可重试 | ✅ 正确 | ✅ |
| 空提示词 | 提交按钮禁用 | ✅ 正确 | ✅ |
| 超长提示词 | 可输入，无限制 | 应限制长度 | ⚠️ |
| 快速双击生成 | 可能重复提交 | 应防抖 | ❌ |
| 生成中关闭页面 | 轮询可能继续 | 应清理 | ✅ |
| 生成中切换历史 | 显示其他视频 | 应提示正在生成 | ⚠️ |
| 浏览器后退 | 可能丢失状态 | 应恢复状态 | ❌ |
| 多标签页同时操作 | 状态不同步 | 应同步或提示 | ❌ |
| 视频加载失败 | 显示错误 | ✅ 正确 | ✅ |

---

## 5️⃣ 交互细节问题

### 键盘导航

| 快捷键 | 功能 | 问题 |
|--------|------|------|
| `/` | 聚焦输入框 | ✅ 正确 |
| `Enter` | 提交 | ✅ 正确 |
| `Shift+Enter` | 换行 | ✅ 正确 |
| `ESC` | 关闭面板 | ✅ 正确 |
| `H` | 打开历史 | ⚠️ 无提示 |
| `S` | 打开设置 | ⚠️ 无提示 |
| `T` | 切换主题 | ⚠️ 无提示 |
| `Ctrl+R` | 刷新 | ❌ 会丢失生成状态 |

**建议**: 添加快捷键提示面板（`?` 键触发）

---

### 加载状态

| 场景 | 当前反馈 | 建议 |
|------|---------|------|
| 初始加载 | LoadingScreen | ✅ 正确 |
| 提交生成 | 按钮变loading | ✅ 正确 |
| 轮询等待 | 进度条 | ✅ 正确 |
| 视频加载 | 无loading | 应添加 |
| 历史加载 | 无loading | 应添加骨架屏 |

---

## 6️⃣ 与竞品工作流对比

| 特性 | easy-manim | Midjourney | Runway | Pika |
|------|------------|------------|--------|------|
| 提示词输入 | 文本框 | 文本框 | 文本框 | 文本框 |
| 参数设置 | 设置面板 | 命令后缀 | 侧边栏 | 底部选项 |
| 生成确认 | 无 | 无 | 无 | 无 |
| 取消生成 | ❌ 无 | ✅ 有 | ✅ 有 | ✅ 有 |
| 批量生成 | ❌ 无 | ✅ 有 | ❌ 无 | ❌ 无 |
| 结果对比 | ❌ 无 | ✅ 网格 | ✅ 时间轴 | ❌ 无 |
| 历史管理 | 侧滑抽屉 | 侧边栏 | 项目制 | 简单列表 |

---

## 7️⃣ 修复建议（按优先级）

### 🔴 高优先级（影响核心体验）

1. **连接参数设置与提交**
   ```typescript
   const result = await createTask({
     prompt: prompt.trim(),
     ...generationParams,
   }, sessionToken);
   ```

2. **添加取消生成功能**
   ```typescript
   const handleCancel = async () => {
     if (currentTask?.id) {
       await cancelTask(currentTask.id, sessionToken);
       pollCleanupRef.current?.();
       setIsGenerating(false);
     }
   };
   ```

3. **添加快捷键提示**
   - 按 `?` 显示快捷键面板
   - 或在工具栏添加帮助按钮

### 🟡 中优先级（提升体验）

4. **添加入字数统计和限制**
5. **改进快捷提示交互**（追加/替换模式）
6. **添加浏览器状态恢复**（beforeunload 提示）

### 🟢 低优先级（锦上添花）

7. **批量生成支持**
8. **结果对比功能**
9. **多标签页状态同步**

---

## ✅ 总结

**当前状态**: 工作流完整，但细节有瑕疵

**核心问题**:
1. 参数设置未实际生效（最严重）
2. 无法取消生成
3. 并发控制不足
4. 边界情况处理不完善

**修复后预期评分**: 7.0 → 8.0
