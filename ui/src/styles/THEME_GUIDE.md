# 宫崎骏主题系统指南

## 概述

本项目采用宫崎骏风格的主题系统，支持白天/夜间模式切换。

## 文件结构

```
src/styles/
├── ghibli-theme.css    # 主主题文件（白天/夜间模式）
└── THEME_GUIDE.md      # 本指南
```

## CSS 变量

### 基础变量（在 `:root` 中定义）

| 变量 | 说明 | 白天默认值 | 夜间默认值 |
|------|------|-----------|-----------|
| `--duration-*` | 动画时长 | 0.1s - 20s | 相同 |
| `--ease-*` | 缓动函数 | 多种 | 相同 |
| `--radius-*` | 圆角 | 12px - 9999px | 相同 |
| `--shadow-*` | 阴影 | 柔和阴影 | 相同 |
| `--space-*` | 间距 | 0.25rem - 6rem | 相同 |

### 主题变量

#### 天空背景
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--sky-top` | #E8F4F8 | #0a0e1a |
| `--sky-mid` | #F0F7FA | #121829 |
| `--sky-bottom` | #FFF8F0 | #1a2332 |

#### 自然色彩
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--grass-light` | #C8E6C9 | #1e3a1e |
| `--grass-mid` | #A5D6A7 | #2d5a2d |
| `--grass-dark` | #81C784 | #3d7a3d |
| `--cloud` | #FFFFFF | rgba(200, 210, 230, 0.15) |
| `--star` | (不存在) | #fff8e7 |
| `--moon` | (不存在) | #fff5d6 |
| `--moon-glow` | (不存在) | rgba(255, 245, 214, 0.25) |

#### 功能色
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--accent-primary` | #7CB342 | #8bc34a |
| `--accent-secondary` | #5C6BC0 | #7986cb |
| `--accent-warm` | #FF8A65 | #ffab91 |

#### 文字颜色
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--text-primary` | #4E342E | #ffffff |
| `--text-secondary` | #6D4C41 | #c8d0e0 |
| `--text-muted` | #9E8B7D | #8890a0 |

#### 表面颜色
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--surface-primary` | rgba(255,255,255,0.85) | rgba(20,28,40,0.95) |
| `--surface-secondary` | rgba(255,255,255,0.6) | rgba(30,40,55,0.85) |
| `--surface-tertiary` | rgba(255,255,255,0.35) | rgba(40,52,70,0.7) |
| `--border-subtle` | rgba(141,110,99,0.15) | rgba(100,116,139,0.25) |

#### 状态颜色
| 变量 | 白天 | 夜间 |
|------|------|------|
| `--status-success` | #66BB6A | #81c784 |
| `--status-warning` | #FFB74D | #ffb74d |
| `--status-error` | #E57373 | #ef5350 |
| `--status-info` | #64B5F6 | #4fc3f7 |

## 使用方式

### 在组件中使用

```tsx
// 直接使用 CSS 变量
<div style={{ color: 'var(--text-primary)' }}>
  文本内容
</div>
```

### 在 CSS Modules 中使用

```css
.container {
  background: var(--surface-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
}
```

## 切换主题

使用 `useTheme` hook：

```tsx
import { useTheme } from '../studio/hooks/useTheme';

function MyComponent() {
  const { isNight, toggleTheme } = useTheme();
  
  return (
    <button onClick={toggleTheme}>
      {isNight ? '切换到白天' : '切换到夜间'}
    </button>
  );
}
```

## 兼容性

为确保与其他组件兼容，主题系统提供了以下别名：

- `--success`, `--warning`, `--error`, `--info` → 状态色别名
- `--glass-border`, `--glass-bg` → 玻璃态效果别名
- `--primary-900`, `--primary-800`, `--accent-cyan` → 深海主题兼容

## 最佳实践

1. **始终使用 CSS 变量**，不要硬编码颜色
2. **测试两种模式**下的显示效果
3. **确保对比度**符合 WCAG 标准
4. **尊重用户偏好**，支持 `prefers-color-scheme` 和 `prefers-reduced-motion`

## 夜间模式设计原则

1. **深色但不纯黑**：使用深蓝灰色 (#0a0e1a) 而非纯黑
2. **降低饱和度**：花朵、装饰元素使用半透明颜色
3. **提高对比度**：文字使用纯白和浅灰，确保可读性
4. **柔和的高光**：使用柔和的星光和月光效果
