# easy-manim UI V2 重构设计

## 设计愿景

打造一款具有未来感的 AI 视频创作控制台，融合深色玻璃态美学与流畅的动态交互，体现"智能体工作流"的科技感和专业性。

## 设计语言: 深蓝玻璃态 (Deep Ocean Glass)

### 色彩系统

```css
/* 主色调 - 深海蓝 */
--primary-900: #0a0f1a;    /* 主背景 */
--primary-800: #0f1729;    /* 卡片背景 */
--primary-700: #1a2332;    /* 悬浮背景 */
--primary-600: #243447;    /* 边框 */

/* 强调色 - 极光渐变 */
--accent-cyan: #00d4ff;
--accent-purple: #8b5cf6;
--accent-pink: #ec4899;
--accent-blue: #3b82f6;

/* 功能色 */
--success: #10b981;
--warning: #f59e0b;
--error: #ef4444;
--info: #00d4ff;

/* 文字 */
--text-primary: #f8fafc;
--text-secondary: #94a3b8;
--text-muted: #64748b;
```

### 玻璃态效果

```css
/* 基础玻璃 */
.glass {
  background: rgba(15, 23, 41, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* 强调玻璃 */
.glass-accent {
  background: linear-gradient(135deg, 
    rgba(0, 212, 255, 0.1) 0%, 
    rgba(139, 92, 246, 0.1) 100%);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.2);
}
```

## 布局架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Navbar (Glass)                                                  │
│  [Logo]              [Search]              [Status] [Profile]   │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│ Sidebar  │  Main Content                                        │
│ (Glass)  │  ┌────────────────────────────────────────────────┐ │
│          │  │ Hero Section | Metrics                          │ │
│ [Tasks]  │  └────────────────────────────────────────────────┘ │
│ [Videos] │                                                      │
│ [Memory] │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│ [Profile]│  │   Card 1     │  │   Card 2     │  │   Card 3   │ │
│ [Evals]  │  │   (Glass)    │  │   (Glass)    │  │  (Glass)   │ │
│          │  └──────────────┘  └──────────────┘  └────────────┘ │
│          │                                                      │
│          │  ┌────────────────────────────────────────────────┐ │
│          │  │ Content Area                                    │ │
│          │  │                                                 │ │
│          │  └────────────────────────────────────────────────┘ │
│          │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

## 动效规范

### 入场动画
- **页面切换**: Fade + SlideUp (duration: 400ms, easing: cubic-bezier(0.4, 0, 0.2, 1))
- **卡片加载**: Stagger fade in (delay: 50ms each, duration: 300ms)
- **数据加载**: Skeleton shimmer effect

### 交互动画
- **Hover**: Scale(1.02) + Glow effect (duration: 200ms)
- **Click**: Scale(0.98) → Scale(1) (duration: 150ms)
- **Focus**: Border glow pulse
- **Status change**: Smooth color transition

### 背景动效
- **渐变背景**: 缓慢的 Aurora 流动效果 (20s loop)
- **粒子网格**: 微妙的连接线网络 (opacity: 0.1)

## 组件规范

### 1. 导航卡片 (NavCard)
- 玻璃态背景
- 左侧发光指示条 (激活状态)
- Hover: 轻微上浮 + 光晕扩散

### 2. 数据卡片 (MetricCard)
- 渐变顶部边框
- 数字计数动画
- 趋势指示器 (up/down)

### 3. 视频卡片 (VideoCard)
- 16:9 视频预览
- 悬浮控制栏 (播放/下载/修订)
- 状态光环 (根据状态变化颜色)

### 4. 任务项 (TaskItem)
- 进度条集成
- 实时状态脉冲点
- 快速操作按钮组

### 5. 输入框 (Input)
- 底部发光边框
- Focus: 全边框发光
- 浮动标签

## 页面设计

### 登录页
- 全屏 Aurora 背景动画
- 中央玻璃卡片
- 粒子连线背景
- 输入框发光效果

### 任务页
- Hero: 快速创建区 + 实时统计
- 视频预览流 (水平滚动)
- 任务队列 (可拖拽排序)
- 最近活动时间线

### 视频页
- 瀑布流/网格切换
- 视频播放器 Lightbox
- 批量操作工具栏
- 智能筛选器

### 记忆页
- 记忆图谱可视化
- 时间轴展示
- 关联度指示

## 技术实现

### 新增依赖
```json
{
  "framer-motion": "^11.x",
  "lucide-react": "^0.x",
  "@radix-ui/react-*": "latest"
}
```

### CSS 架构
- CSS Variables for theming
- Tailwind-style utility classes
- CSS Animations for performance

### 响应式断点
- Mobile: < 640px (单列)
- Tablet: 640px - 1024px (双列)
- Desktop: > 1024px (完整布局)
