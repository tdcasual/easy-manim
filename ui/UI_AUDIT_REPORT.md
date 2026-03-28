# 🎨 easy-manim Studio V3 - UI/UX 审计报告

**审计日期**: 2026-03-27  
**审计范围**: Studio 新界面（宫崎骏风格）  
**审计人员**: Code Reviewer

---

## 📊 执行摘要

| 维度 | 评分 | 说明 |
|------|------|------|
| **代码质量** | 7/10 | 功能实现完整，但有多个需要修复的问题 |
| **可访问性** | 5/10 | ARIA 支持不足，键盘导航有缺陷 |
| **性能** | 6/10 | 动画较多，部分可能影响低端设备 |
| **用户体验** | 7/10 | 界面美观，但交互细节需要完善 |
| **响应式** | 6/10 | 基础适配存在，但移动端体验欠佳 |

---

## 🔴 严重问题 (Critical)

### C1: 历史抽屉缩略图 XSS 漏洞
**位置**: `HistoryDrawer.tsx:270`

**问题代码**:
```tsx
background: item.thumbnailUrl 
  ? `url(${item.thumbnailUrl}) center/cover` 
  : "var(--surface-tertiary)",
```

**风险**: `thumbnailUrl` 直接插入 CSS，如果 URL 包含恶意代码（如 `javascript:` 协议），可能导致 XSS 攻击。

**修复**:
```tsx
// 添加 URL 验证
const isValidUrl = (url: string) => {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

background: (item.thumbnailUrl && isValidUrl(item.thumbnailUrl))
  ? `url(${item.thumbnailUrl}) center/cover`
  : "var(--surface-tertiary)",
```

---

### C2: 未认证状态处理缺失
**位置**: `Studio.tsx:170-172`

**问题**: 未登录时显示空白页面，没有引导用户登录。

**修复**:
```tsx
if (!isReady) {
  return <LoadingScreen />;
}

if (!sessionToken) {
  return <Navigate to="/login" replace />;
}
```

---

## 🟠 高优先级问题 (High)

### H1: 轮询逻辑未清理
**位置**: `Studio.tsx:118-142`

**问题**: `pollTaskStatus` 使用 `setTimeout` 但没有清理机制，组件卸载后继续执行可能导致内存泄漏和状态更新错误。

**修复**:
```tsx
const pollTaskStatus = useCallback(async (taskId: string) => {
  if (!sessionToken) return;
  
  let timeoutId: number;
  let isCancelled = false;

  const checkStatus = async () => {
    if (isCancelled) return;
    
    try {
      const response = await getTask(taskId, sessionToken);
      if (isCancelled) return;
      
      if (response.status === "completed") {
        setCurrentTask(prev => ({ ...prev, status: "completed" }));
        setIsGenerating(false);
        loadHistory();
      } else if (["running", "queued"].includes(response.status)) {
        timeoutId = window.setTimeout(checkStatus, 3000);
      }
    } catch {
      if (!isCancelled) setIsGenerating(false);
    }
  };

  checkStatus();
  
  return () => {
    isCancelled = true;
    clearTimeout(timeoutId);
  };
}, [sessionToken, loadHistory]);

// 在 useEffect 中使用
useEffect(() => {
  if (currentTask?.status === "running") {
    const cleanup = pollTaskStatus(currentTask.id);
    return cleanup;
  }
}, [currentTask?.id, currentTask?.status]);
```

---

### H2: 输入框高度调整问题
**位置**: `ChatInput.tsx:71-77`

**问题**: 自动调整高度逻辑在内容减少时不会缩小。

**当前代码**:
```tsx
const adjustHeight = useCallback(() => {
  const textarea = textareaRef.current;
  if (!textarea) return;
  
  textarea.style.height = "auto";  // 重置
  textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
}, []);
```

**问题**: `rows={1}` 在 JSX 中限制了最小高度，当内容清空时不会回到 1 行高度。

**修复**:
```tsx
const adjustHeight = useCallback(() => {
  const textarea = textareaRef.current;
  if (!textarea) return;
  
  textarea.style.height = "auto";
  const newHeight = Math.max(40, Math.min(textarea.scrollHeight, 150));
  textarea.style.height = `${newHeight}px`;
}, []);

// 组件卸载时清理
useEffect(() => {
  return () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };
}, []);
```

---

### H3: 视频播放状态不同步
**位置**: `VideoStage.tsx:191-205`

**问题**: 外部控制视频状态（如从其他组件播放）时，`isPlaying` 状态可能不一致。

**修复**:
```tsx
// 添加对 video 属性的监听
useEffect(() => {
  const video = videoRef.current;
  if (!video) return;

  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);

  video.addEventListener("play", handlePlay);
  video.addEventListener("pause", handlePause);

  return () => {
    video.removeEventListener("play", handlePlay);
    video.removeEventListener("pause", handlePause);
  };
}, []);
```

---

## 🟡 中优先级问题 (Medium)

### M1: ARIA 属性缺失
**位置**: 多个组件

| 组件 | 问题 | 修复 |
|------|------|------|
| `VideoStage` | 播放按钮缺少 `aria-label` | 添加 `aria-label={isPlaying ? "暂停" : "播放"}` |
| `ThemeToggle` | 按钮缺少 `aria-pressed` | 添加 `aria-pressed={isNight}` |
| `HistoryDrawer` | 抽屉缺少 `role="dialog"` | 添加角色和 `aria-modal` |
| `ChatInput` | 快捷提示不是按钮 | 添加 `role="button"` 和 `tabIndex` |

---

### M2: 键盘导航问题
**位置**: `HistoryDrawer.tsx`

**问题**: 抽屉打开后，焦点没有自动转移到抽屉内，Tab 导航可能逃出抽屉。

**修复**: 实现焦点陷阱（Focus Trap）：
```tsx
useEffect(() => {
  if (!isOpen) return;

  const drawer = drawerRef.current;
  if (!drawer) return;

  // 获取所有可聚焦元素
  const focusableElements = drawer.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  // 聚焦第一个元素
  firstElement?.focus();

  const handleTabKey = (e: KeyboardEvent) => {
    if (e.key !== "Tab") return;

    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault();
      lastElement?.focus();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault();
      firstElement?.focus();
    }
  };

  drawer.addEventListener("keydown", handleTabKey);
  return () => drawer.removeEventListener("keydown", handleTabKey);
}, [isOpen]);
```

---

### M3: 移动端触摸反馈缺失
**位置**: 多个按钮组件

**问题**: 移动端没有 `:active` 状态的触摸反馈，用户不确定是否点击成功。

**修复**: 添加 `@media (hover: none)` 样式：
```css
@media (hover: none) {
  .btn-ghibli:active {
    transform: scale(0.96);
    opacity: 0.8;
  }
}
```

---

### M4: 动画性能优化
**位置**: `SkyBackground.tsx`

**问题**: 
- 云朵动画使用 `left` 属性，触发重排（reflow）
- 30 个星星同时动画可能消耗 CPU

**修复**:
```tsx
// 使用 transform 代替 left
function Cloud({ size, top, duration, delay, opacity, layer }: CloudProps) {
  const style: React.CSSProperties = {
    position: "absolute",
    top,
    left: 0,
    width: `${size}px`,
    height: `${size * 0.5}px`,
    opacity,
    color: "var(--cloud)",
    filter: `drop-shadow(0 ${4 * layer}px ${8 * layer}px var(--cloud-shadow))`,
    animation: `drift-transform ${duration}s linear infinite`,
    animationDelay: `${delay}s`,
    zIndex: layer,
    transform: "translateX(-100%)",  // 初始位置
  };
  // ...
}

// CSS
@keyframes drift-transform {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(calc(100vw + 100%));
  }
}
```

---

### M5: 错误处理不完善
**位置**: `Studio.tsx:112-115`

**问题**: 创建任务失败只打印日志，用户看不到错误提示。

**修复**:
```tsx
const [error, setError] = useState<string | null>(null);

// 提交时
try {
  // ...
} catch (err) {
  setError(err instanceof Error ? err.message : "创建失败，请重试");
  setIsGenerating(false);
}

// UI 中显示错误
{error && (
  <div role="alert" className="error-message">
    {error}
  </div>
)}
```

---

## 🟢 低优先级问题 (Low)

### L1: 主题切换闪烁
**位置**: `index.html`

**问题**: 主题切换时可能有短暂闪烁。

**修复**: 在 HTML 中预置主题 CSS：
```html
<style>
  html[data-theme="night"] {
    background: linear-gradient(180deg, #1A237E 0%, #283593 50%, #3F51B5 100%);
  }
</style>
```

---

### L2: 草丛位置重叠
**位置**: `SkyBackground.tsx:276-287`

**问题**: 草丛随机生成可能重叠在一起。

**建议**: 使用简单的网格布局避免重叠，或者减少草丛数量。

---

### L3: 缺少加载骨架屏
**位置**: `Studio.tsx`

**问题**: 初始加载历史时没有骨架屏，直接空白。

---

### L4: 视频标题过长截断
**位置**: `VideoStage.tsx:304-322`

**问题**: 标题过长时没有截断处理。

**修复**:
```tsx
<div style={{
  maxWidth: "80%",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}}>
  {title}
</div>
```

---

## 📱 响应式问题

### R1: 小屏幕视频舞台过大
**位置**: `VideoStage.tsx:218`

**问题**: `aspectRatio: "16 / 10"` 在小屏幕上可能超出视口。

**修复**:
```css
@media (max-width: 640px) {
  .video-stage {
    aspect-ratio: 4 / 3;
    max-height: 50vh;
  }
}
```

---

### R2: 输入框在虚拟键盘弹出时
**位置**: `ChatInput.tsx`

**问题**: 移动端键盘弹出时，输入框可能被遮挡。

**建议**: 使用 `visualViewport` API 监听键盘高度变化。

---

## 🔧 代码风格问题

### S1: 魔法数字
**位置**: 多个文件

问题代码中的数字应该提取为常量：
```tsx
// 不好的
width: "44px",
height: "44px",

// 好的
const LOGO_SIZE = 44;
width: `${LOGO_SIZE}px`,
```

---

### S2: 内联样式过多
**位置**: 所有组件

**建议**: 将重复样式提取为 CSS 类，使用 CSS Modules 或 styled-components。

---

## 📋 改进建议

### 1. 添加骨架屏加载
```tsx
function StudioSkeleton() {
  return (
    <div className="studio-skeleton">
      <div className="skeleton-header" />
      <div className="skeleton-video" />
      <div className="skeleton-input" />
    </div>
  );
}
```

### 2. 添加撤销操作
```tsx
const [lastPrompt, setLastPrompt] = useState("");

const handleUndo = () => {
  setPrompt(lastPrompt);
};
```

### 3. 添加拖拽上传
```tsx
const [isDragging, setIsDragging] = useState(false);

<div
  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
  onDrop={(e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    // 处理上传
  }}
>
```

---

## ✅ 修复清单

### 必须修复（发布前）
- [ ] C1: XSS 漏洞
- [ ] C2: 未认证状态处理
- [ ] H1: 轮询清理
- [ ] H2: 输入框高度
- [ ] H3: 视频状态同步

### 建议修复（1周内）
- [ ] M1: ARIA 属性
- [ ] M2: 键盘导航
- [ ] M3: 触摸反馈
- [ ] M4: 动画性能
- [ ] M5: 错误提示

### 可选优化
- [ ] L1-L4
- [ ] R1-R2
- [ ] S1-S2

---

## 📊 总体评价

新的 Studio 界面视觉上非常吸引人，成功实现了宫崎骏风格的设计愿景。但在可访问性、性能优化和错误处理方面还有改进空间。

**优点**:
- 设计美观，风格统一
- 动画丰富，体验流畅
- 代码结构清晰

**需要改进**:
- 可访问性支持不足
- 错误处理不完善
- 移动端适配需要加强

**建议**: 在发布前至少修复所有严重和高优先级问题。
