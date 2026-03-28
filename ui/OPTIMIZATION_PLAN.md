# UI 优化执行方案

## 执行策略

分 4 个阶段实施，每阶段独立可交付：

| 阶段 | 内容 | 工时 | 优先级 |
|------|------|------|--------|
| Phase 1 | 关键体验优化 (Toast、Loading、Help) | 4h | P0 |
| Phase 2 | 功能增强 (搜索、表单、筛选) | 10h | P1 |
| Phase 3 | 视觉升级 (动画、装饰、暗黑) | 6h | P2 |
| Phase 4 | 设计系统统一 | 4h | P2 |

---

## Phase 1: 关键体验优化 (P0)

### 1.1 全局 Toast 通知系统

**目标**: 替换 ErrorBanner，提供统一通知体验

**新建文件**: `src/components/Toast.tsx`

```tsx
import { useState, useCallback, createContext, useContext, useEffect } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import "./Toast.css";

type ToastType = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, type: ToastType = "info", duration = 3000) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev, { id, message, type, duration }]);
      setTimeout(() => removeToast(id), duration);
    },
    [removeToast]
  );

  const success = useCallback((message: string, duration?: number) => {
    toast(message, "success", duration);
  }, [toast]);

  const error = useCallback((message: string, duration?: number) => {
    toast(message, "error", duration);
  }, [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error }}>
      {children}
      <div className="toast-container" role="region" aria-label="通知">
        {toasts.map((t) => (
          <Toast key={t.id} item={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function Toast({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, item.duration);
    return () => clearTimeout(timer);
  }, [item.duration, onClose]);

  const icons = {
    success: <CheckCircle size={18} />,
    error: <AlertCircle size={18} />,
    warning: <AlertCircle size={18} />,
    info: <Info size={18} />,
  };

  return (
    <div className={`toast toast-${item.type}`} role="alert">
      <span className="toast-icon">{icons[item.type]}</span>
      <span className="toast-message">{item.message}</span>
      <button className="toast-close" onClick={onClose} aria-label="关闭">
        <X size={14} />
      </button>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
```

**新建文件**: `src/components/Toast.css`

```css
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--surface-primary);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: var(--shadow-heavy);
  min-width: 280px;
  max-width: 400px;
  pointer-events: auto;
  animation: toast-in 0.3s ease;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.toast-success {
  border-color: var(--status-success);
}
.toast-error {
  border-color: var(--status-error);
}
.toast-warning {
  border-color: var(--status-warning);
}

.toast-icon {
  flex-shrink: 0;
}
.toast-success .toast-icon { color: var(--status-success); }
.toast-error .toast-icon { color: var(--status-error); }
.toast-warning .toast-icon { color: var(--status-warning); }

.toast-message {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
}

.toast-close {
  flex-shrink: 0;
  padding: 4px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}
.toast-close:hover {
  background: var(--surface-tertiary);
  color: var(--text-primary);
}
```

**修改**: `src/main.tsx` - 包裹 ToastProvider

```tsx
import { ToastProvider } from "./components/Toast";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ToastProvider>
      <AppRouter />
    </ToastProvider>
  </React.StrictMode>
);
```

---

### 1.2 TasksPage 添加 Loading 和错误反馈

**修改**: `src/features/tasks/TasksPageV2.tsx`

```tsx
// 添加导入
import { useToast } from "../../components/Toast";
import { Loader2 } from "lucide-react";

// 在组件内部
export default function TasksPageV2() {
  const { success, error: showError } = useToast();
  // ... existing code

  // 修改 handleCreate
  async function handleCreate(promptText: string) {
    if (!sessionToken || !promptText.trim()) return;
    setCreating(true);
    try {
      const result = await createTask(promptText, sessionToken);
      success(`任务 ${result.task_id.slice(0, 8)} 创建成功`);
      setPrompt("");
      await loadData();
    } catch (e) {
      showError(e instanceof Error ? e.message : "创建任务失败");
    } finally {
      setCreating(false);
    }
  }

  // 修改 send button
  <button
    type="submit"
    className={`quick-send ${creating ? "loading" : ""}`}
    disabled={creating || !prompt.trim()}
  >
    {creating ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
  </button>;
}
```

**添加 CSS**: `src/features/tasks/TasksPageV2.css`

```css
.quick-send.loading {
  opacity: 0.7;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

### 1.3 Studio 添加 Help 按钮入口

**修改**: `src/studio/Studio.tsx`

```tsx
// 添加导入
import { HelpCircle } from "lucide-react";

// 在 Header 工具栏添加
<div className={styles.toolbar}>
  {/* 现有按钮 */}
  <button
    type="button"
    className={styles.toolbarButton}
    onClick={toggleHistory}
    aria-label="历史"
  >
    <History size={20} />
    <span>历史</span>
  </button>
  
  {/* 新增帮助按钮 */}
  <button
    type="button"
    className={styles.toolbarButton}
    onClick={toggleHelp}
    aria-label="帮助"
    title="快捷键 ?"
  >
    <HelpCircle size={20} />
    <span>帮助</span>
  </button>
  
  <button
    type="button"
    className={styles.toolbarButton}
    onClick={toggleSettings}
    aria-label="设置"
  >
    <Settings size={20} />
    <span>设置</span>
  </button>
</div>
```

---

## Phase 2: 功能增强 (P1)

### 2.1 VideosPage 搜索筛选功能

**新建组件**: `src/features/videos/VideoFilterBar.tsx`

```tsx
import { useState } from "react";
import { Search, Filter } from "lucide-react";

interface VideoFilterBarProps {
  onSearch: (query: string) => void;
  onStatusFilter: (status: string) => void;
  onViewModeChange: (mode: "grid" | "list") => void;
  viewMode: "grid" | "list";
}

export function VideoFilterBar({
  onSearch,
  onStatusFilter,
  onViewModeChange,
  viewMode,
}: VideoFilterBarProps) {
  const [query, setQuery] = useState("");

  return (
    <div className="video-filter-bar">
      <div className="search-box">
        <Search size={16} />
        <input
          type="text"
          placeholder="搜索视频..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onSearch(e.target.value);
          }}
        />
      </div>
      
      <select onChange={(e) => onStatusFilter(e.target.value)}>
        <option value="">全部状态</option>
        <option value="completed">已完成</option>
        <option value="processing">处理中</option>
        <option value="failed">失败</option>
      </select>
      
      <div className="view-toggle">
        <button
          className={viewMode === "grid" ? "active" : ""}
          onClick={() => onViewModeChange("grid")}
        >
          网格
        </button>
        <button
          className={viewMode === "list" ? "active" : ""}
          onClick={() => onViewModeChange("list")}
        >
          列表
        </button>
      </div>
    </div>
  );
}
```

**新建组件**: `src/features/videos/VideoListItem.tsx`

```tsx
import { Play, Clock, CheckCircle } from "lucide-react";
import { resolveApiUrl } from "../../lib/api";

interface VideoListItemProps {
  video: {
    task_id: string;
    download_url: string;
    created_at: string;
    status: string;
  };
}

export function VideoListItem({ video }: VideoListItemProps) {
  return (
    <div className="video-list-item">
      <div className="video-thumb">
        <video src={resolveApiUrl(video.download_url) || undefined} preload="metadata" />
        <span className="play-overlay">
          <Play size={24} />
        </span>
      </div>
      <div className="video-info">
        <h4>{video.task_id}</h4>
        <div className="meta">
          <span><Clock size={12} /> {new Date(video.created_at).toLocaleDateString()}</span>
          <span className={`status ${video.status}`}>
            {video.status === "completed" && <CheckCircle size={12} />}
            {video.status}
          </span>
        </div>
      </div>
    </div>
  );
}
```

---

### 2.2 ProfilePage 可视化编辑器

**新建组件**: `src/features/profile/VisualProfileEditor.tsx`

```tsx
import { useState } from "react";

interface ProfileData {
  style_hints?: string[];
  default_quality?: string;
  auto_save?: boolean;
}

interface VisualProfileEditorProps {
  data: ProfileData;
  onChange: (data: ProfileData) => void;
}

export function VisualProfileEditor({ data, onChange }: VisualProfileEditorProps) {
  const [formData, setFormData] = useState<ProfileData>(data);

  const updateField = <K extends keyof ProfileData>(key: K, value: ProfileData[K]) => {
    const newData = { ...formData, [key]: value };
    setFormData(newData);
    onChange(newData);
  };

  return (
    <div className="visual-profile-editor">
      <div className="form-group">
        <label>默认质量</label>
        <select
          value={formData.default_quality || "high"}
          onChange={(e) => updateField("default_quality", e.target.value)}
        >
          <option value="standard">标准</option>
          <option value="high">高清</option>
          <option value="ultra">超清</option>
        </select>
      </div>

      <div className="form-group">
        <label>风格偏好</label>
        <div className="tag-input">
          {(formData.style_hints || []).map((hint, i) => (
            <span key={i} className="tag">
              {hint}
              <button onClick={() => {
                const newHints = formData.style_hints?.filter((_, idx) => idx !== i);
                updateField("style_hints", newHints);
              }}>×</button>
            </span>
          ))}
          <input
            type="text"
            placeholder="添加风格..."
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const value = e.currentTarget.value.trim();
                if (value) {
                  updateField("style_hints", [...(formData.style_hints || []), value]);
                  e.currentTarget.value = "";
                }
              }
            }}
          />
        </div>
      </div>

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.auto_save || false}
            onChange={(e) => updateField("auto_save", e.target.checked)}
          />
          自动保存
        </label>
      </div>
    </div>
  );
}
```

---

## Phase 3: 视觉升级 (P2)

### 3.1 添加渐变背景装饰

**新建**: `src/components/GradientBackground.tsx`

```tsx
export function GradientBackground() {
  return (
    <div className="gradient-background" aria-hidden="true">
      <div className="gradient-orb orb-1" />
      <div className="gradient-orb orb-2" />
      <div className="gradient-orb orb-3" />
    </div>
  );
}
```

**CSS**: `src/components/GradientBackground.css`

```css
.gradient-background {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: -1;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #7cb342 0%, #4caf50 100%);
  top: -200px;
  right: -200px;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #e040fb 0%, #9c27b0 100%);
  bottom: -100px;
  left: -100px;
  animation-delay: -7s;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #ff9800 0%, #ff5722 100%);
  top: 50%;
  left: 50%;
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

@media (prefers-reduced-motion: reduce) {
  .gradient-orb {
    animation: none;
  }
}
```

---

### 3.2 增强二次元风格标签

**新建**: `src/components/KawaiiTag.tsx`

```tsx
interface KawaiiTagProps {
  children: React.ReactNode;
  color?: "green" | "pink" | "blue" | "purple" | "orange";
  size?: "sm" | "md";
  icon?: React.ReactNode;
}

export function KawaiiTag({ children, color = "green", size = "md", icon }: KawaiiTagProps) {
  return (
    <span className={`kawaii-tag ${color} ${size}`}>
      {icon && <span className="tag-icon">{icon}</span>}
      <span className="tag-text">{children}</span>
    </span>
  );
}
```

**CSS**:

```css
.kawaii-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  border: 2px solid transparent;
  box-shadow: 0 2px 0 rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.kawaii-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 0 rgba(0,0,0,0.1);
}

.kawaii-tag.green {
  background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%);
  color: #2e7d32;
  border-color: #4caf50;
}

.kawaii-tag.pink {
  background: linear-gradient(135deg, #f8bbd9 0%, #f48fb1 100%);
  color: #c2185b;
  border-color: #e91e63;
}

.kawaii-tag.blue {
  background: linear-gradient(135deg, #bbdefb 0%, #90caf9 100%);
  color: #1565c0;
  border-color: #2196f3;
}

.tag-icon {
  display: flex;
  align-items: center;
}
```

---

## Phase 4: 设计系统统一

### 4.1 创建设计 Token 文件

**新建**: `src/styles/tokens.css`

```css
:root {
  /* 主色板 */
  --color-primary-50: #f1f8e9;
  --color-primary-100: #dcedc8;
  --color-primary-500: #7cb342;
  --color-primary-600: #689f38;
  --color-primary-700: #558b2f;

  /* 辅助色 */
  --color-secondary-pink: #e040fb;
  --color-secondary-blue: #448aff;
  --color-secondary-orange: #ff9100;

  /* 间距系统 (4px 基准) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* 圆角系统 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* 阴影系统 */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --shadow-glow: 0 0 20px rgba(124, 179, 66, 0.3);

  /* 动画 */
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 350ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);

  /* Z-index */
  --z-base: 0;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-modal: 300;
  --z-popover: 400;
  --z-tooltip: 500;
  --z-toast: 600;
}
```

### 4.2 创建通用 Button 组件

**新建**: `src/components/Button/Button.tsx`

```tsx
import { forwardRef } from "react";
import styles from "./Button.module.css";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, icon, children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`${styles.button} ${styles[variant]} ${styles[size]} ${loading ? styles.loading : ""} ${className || ""}`}
        disabled={props.disabled || loading}
        {...props}
      >
        {loading && <span className={styles.spinner} />}
        {!loading && icon && <span className={styles.icon}>{icon}</span>}
        <span className={styles.content}>{children}</span>
      </button>
    );
  }
);

Button.displayName = "Button";
```

**CSS Module**: `src/components/Button/Button.module.css`

```css
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: var(--radius-lg);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.1);
}

.button:active {
  transform: translateY(2px);
  box-shadow: none;
}

/* Variants */
.primary {
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
  color: white;
}
.primary:hover {
  background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-primary-700) 100%);
}

.secondary {
  background: var(--surface-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
}

.ghost {
  background: transparent;
  color: var(--text-secondary);
  box-shadow: none;
}
.ghost:hover {
  background: var(--surface-secondary);
}

/* Sizes */
.sm {
  padding: 6px 12px;
  font-size: 12px;
  min-height: 32px;
}
.md {
  padding: 10px 16px;
  font-size: 14px;
  min-height: 40px;
}
.lg {
  padding: 14px 24px;
  font-size: 16px;
  min-height: 48px;
}

/* Loading state */
.loading {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 实施检查清单

### Phase 1 (P0)
- [ ] 创建 Toast 组件
- [ ] 集成 ToastProvider
- [ ] TasksPage 添加 loading 和错误提示
- [ ] Studio 添加 Help 按钮
- [ ] 测试所有通知场景

### Phase 2 (P1)
- [ ] 创建 VideoFilterBar 组件
- [ ] 创建 VideoListItem 组件
- [ ] 创建 VisualProfileEditor 组件
- [ ] 集成到对应页面
- [ ] 添加筛选逻辑

### Phase 3 (P2)
- [ ] 创建 GradientBackground 组件
- [ ] 创建 KawaiiTag 组件
- [ ] 应用渐变背景到主要页面
- [ ] 测试 prefers-reduced-motion

### Phase 4
- [ ] 创建 tokens.css
- [ ] 创建 Button 组件
- [ ] 替换现有按钮
- [ ] 更新所有 CSS 使用 token

---

## 预期效果

| 指标 | 当前 | 优化后 |
|------|------|--------|
| 错误反馈 | 静默/控制台 | Toast 即时通知 |
| 按钮交互 | 无 loading 态 | 统一 loading 动画 |
| 视觉一致性 | 风格混杂 | 统一设计系统 |
| 二次元风格 | 基础圆角 | 渐变+动效+装饰 |
| 移动端体验 | 触摸区域小 | ≥44px 标准 |
