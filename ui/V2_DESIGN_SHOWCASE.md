# easy-manim UI V2 设计展示

## 设计理念

> "从温暖的纸张质感，进化为未来的玻璃态空间"

V2 设计将原有的温暖米色主题升级为**深海玻璃态 (Deep Ocean Glass)** 风格，体现 AI 视频生成平台的科技感与专业性。

---

## 视觉对比

### 登录页对比

| V1 (原设计) | V2 (新设计) |
|:-----------:|:-----------:|
| 米色温暖背景 | 深海蓝 + Aurora 渐变 |
| 纸质质感卡片 | 玻璃态模糊卡片 |
| 静态背景 | Canvas 粒子动画 |
| 传统表单 | 发光输入框 |

### 主界面对比

| V1 (原设计) | V2 (新设计) |
|:-----------:|:-----------:|
| 侧边导航（米色） | 玻璃态侧边栏（深蓝） |
| 圆角大卡片 | 玻璃态卡片 + 渐变边框 |
| 静态状态标签 | 脉冲动画状态点 |
| 简单悬停效果 | 光晕 + 上浮 + 阴影 |

---

## 新设计亮点

### 1. 🌌 Aurora 动态背景
```css
/* 流动极光效果 */
background:
  radial-gradient(ellipse 80% 50% at 20% 40%, rgba(0, 212, 255, 0.2), transparent),
  radial-gradient(ellipse 60% 40% at 80% 60%, rgba(139, 92, 246, 0.15), transparent);
animation: aurora 20s ease infinite;
```

### 2. ✨ 粒子连线背景（登录页）
- 60 个动态粒子
- 150px 范围内自动连线
- 60fps 流畅动画

### 3. 🎨 玻璃态设计系统
```css
.glass {
  background: rgba(15, 23, 41, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
```

### 4. 💫 动效规范
- **页面入场**: Fade + SlideUp (400ms)
- **卡片悬停**: Scale(1.02) + 光晕扩散
- **状态指示**: 2s 脉冲呼吸动画
- **交错加载**: 50ms 逐级延迟

### 5. 🎯 交互细节
- 视频卡片悬停自动播放
- 导航项悬停显示箭头
- 按钮点击缩放反馈
- 输入框聚焦发光

---

## 页面预览

### 登录页
```
┌─────────────────────────────────────────────────────────────┐
│  [Canvas 粒子背景]         [Aurora 流动动画]                 │
│                                                             │
│    ┌──────┐                                                 │
│    │ Logo │  easy-manim                                     │
│    └──────┘  AI 驱动的数学动画创作平台                      │
│                                                             │
│                    ┌─────────────────────┐                  │
│                    │   欢迎回来           │                  │
│                    │   [Agent Token]      │                  │
│                    │   [  登录  ]          │                  │
│                    └─────────────────────┘                  │
│                        ↑ 玻璃态卡片                          │
└─────────────────────────────────────────────────────────────┘
```

### 任务页
```
┌─────────────────────────────────────────────────────────────┐
│  [顶部栏]  easy-manim console          [状态] [头像]        │
├──────────┬──────────────────────────────────────────────────┤
│          │  创作台                                              │
│  [任务]  │  任务管理                           [刷新]         │
│  [视频]  │  ───────────────────────────────────────────────   │
│  [记忆]  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐             │
│  [画像]  │  │进行中│ │已完成│ │ 失败 │ │ 总计 │  指标卡片    │
│  [评测]  │  └──────┘ └──────┘ └──────┘ └──────┘             │
│          │  ───────────────────────────────────────────────   │
│          │  ┌───────────────────────┐ ┌───────────────────┐ │
│          │  │  新建任务             │ │  最近视频         │ │
│          │  │  [任务描述输入框]     │ │  ┌─────────────┐  │ │
│          │  │  [快速提示] [创建]    │ │  │  视频预览   │  │ │
│          │  │                       │ │  │  标题 状态  │  │ │
│          │  └───────────────────────┘ │  └─────────────┘  │ │
│          │                            └───────────────────┘ │
└──────────┴──────────────────────────────────────────────────┘
    ↑ 玻璃态侧边栏
```

---

## 色彩系统

### 主色调
```
--primary-900: #0a0f1a    (主背景)
--primary-800: #0f1729    (卡片背景)
--primary-700: #1a2332    (悬浮背景)
```

### 强调色
```
--accent-cyan:    #00d4ff    (主要强调)
--accent-purple:  #8b5cf6    (次要强调)
--accent-pink:    #ec4899    (第三强调)
--accent-blue:    #3b82f6    (功能色)
```

### 渐变色
```css
--gradient-aurora: linear-gradient(135deg, 
  #00d4ff 0%, #3b82f6 50%, #8b5cf6 100%);
```

---

## 响应式设计

### Desktop (> 1200px)
- 完整侧边栏 (280px)
- 4 列指标网格
- 双列内容布局

### Tablet (768px - 1200px)
- 可收起侧边栏
- 2 列指标网格
- 单列内容布局

### Mobile (< 768px)
- 隐藏侧边栏
- 1 列指标网格
- 底部导航栏

---

## 技术实现

### 新增依赖
```json
{
  "lucide-react": "^0.454.0"
}
```

### CSS 架构
- CSS Variables 主题系统
- Utility-first 工具类
- Container queries 响应式

### 性能优化
- `transform` 和 `opacity` 动画
- `will-change` 提示
- `backdrop-filter` 适度使用
- Canvas 粒子使用 `requestAnimationFrame`

---

## 文件结构

```
ui/src/
├── styles/
│   ├── theme-v2.css      # 新主题系统
│   └── reset.css         # 原重置样式
├── app/
│   ├── App.tsx           # 重构主组件
│   ├── App.css           # 布局样式
│   └── router.tsx
├── features/
│   ├── auth/
│   │   ├── LoginPageV2.tsx    # 新登录页
│   │   └── LoginPage.css
│   ├── tasks/
│   │   ├── TasksPageV2.tsx    # 新任务页
│   │   ├── TasksPageV2.css
│   │   ├── TaskDetailPageV2.tsx
│   │   └── TaskDetailPageV2.css
│   ├── videos/
│   │   ├── VideosPageV2.tsx   # 新视频页
│   │   └── VideosPageV2.css
│   ├── memory/
│   │   ├── MemoryPageV2.tsx   # 新记忆页
│   │   └── MemoryPageV2.css
│   ├── profile/
│   │   ├── ProfilePageV2.tsx  # 新画像页
│   │   └── ProfilePageV2.css
│   └── evals/
│       ├── EvalsPageV2.tsx    # 新评测页
│       ├── EvalsPageV2.css
│       ├── EvalDetailPageV2.tsx
│       └── EvalDetailPageV2.css
```

---

## 启动方式

```bash
cd ui
npm install
npm run dev
```

访问 http://localhost:5173

---

## 设计参考

- **Linear.app** - 玻璃态设计
- **Vercel Dashboard** - 深色主题
- **Raycast** - 动效设计
- **GitHub Copilot** - Aurora 背景
