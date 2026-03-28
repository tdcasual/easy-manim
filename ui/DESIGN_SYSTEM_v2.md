# Easy-Manim UI 2.0 - 二次元风格设计系统

## 🎨 设计理念

### 核心风格："梦幻工坊"
结合吉卜力的温暖手绘感 + Kawaii的可爱元素 + 现代极简主义

### 设计关键词
- 🌸 **柔和** - 圆润的形状，温暖的色彩
- ✨ **梦幻** - 渐变光效，星星云朵元素
- 🎀 **可爱** -  emoji 图标，动物 mascots
- 🌿 **自然** - 植物元素，有机曲线
- 💫 **轻盈** - 充足留白，呼吸感

---

## 🎯 色彩系统

### 主色调（Primary）
```css
/* 樱花粉 */
--primary-pink: #FFB7C5;
--primary-pink-light: #FFE4E9;
--primary-pink-dark: #FF8FA3;

/* 薄荷绿 */
--primary-mint: #A8E6CF;
--primary-mint-light: #D4F5E9;
--primary-mint-dark: #7FD4B6;

/* 天空蓝 */
--primary-sky: #A8D8EA;
--primary-sky-light: #D4F1F9;
--primary-sky-dark: #7FC4DB;
```

### 辅助色（Secondary）
```css
/* 薰衣草紫 */
--secondary-lavender: #DDA0DD;
--secondary-lavender-light: #F0D4F0;

/* 蜜桃橙 */
--secondary-peach: #FFCBA4;
--secondary-peach-light: #FFE5D4;

/* 柠檬黄 */
--secondary-lemon: #FFFACD;
--secondary-lemon-light: #FFFDE7;
```

### 背景色
```css
/* 日间模式 */
--bg-day: linear-gradient(180deg, #FFF5F7 0%, #F0F9F6 50%, #E8F4F8 100%);

/* 云朵白 */
--bg-cloud: #FFFCFC;
--bg-cloud-warm: #FFFAF5;

/* 半透明玻璃 */
--glass-white: rgba(255, 255, 255, 0.85);
--glass-pink: rgba(255, 228, 233, 0.7);
--glass-mint: rgba(212, 245, 233, 0.7);
```

### 文字色
```css
--text-primary: #4A4A4A;      /* 温暖的深灰 */
--text-secondary: #7A7A7A;    /* 中灰 */
--text-muted: #AAAAAA;        /* 浅灰 */
--text-pink: #FF6B8A;         /* 强调粉 */
```

---

## 🔤 字体系统

### 主字体
```css
/* 标题 - 圆润可爱 */
--font-display: 'Quicksand', 'M PLUS Rounded 1c', sans-serif;

/* 正文 - 清晰可读 */
--font-body: 'Nunito', 'Noto Sans SC', sans-serif;

/* 代码/数据 */
--font-mono: 'JetBrains Mono', monospace;
```

### 字体大小
```css
--text-xs: 0.75rem;    /* 12px - 标签 */
--text-sm: 0.875rem;   /* 14px - 辅助文字 */
--text-base: 1rem;     /* 16px - 正文 */
--text-lg: 1.125rem;   /* 18px - 小标题 */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px - 标题 */
--text-3xl: 1.875rem;  /* 30px */
--text-4xl: 2.25rem;   /* 36px - 大标题 */
```

---

## 🎭 形状系统

### 圆角
```css
--radius-sm: 8px;      /* 小元素 */
--radius-md: 16px;     /* 按钮、输入框 */
--radius-lg: 24px;     /* 卡片 */
--radius-xl: 32px;     /* 大卡片 */
--radius-full: 9999px; /* 圆形 */
--radius-blob: 60% 40% 30% 70% / 60% 30% 70% 40%; /* 有机形状 */
```

### 阴影
```css
/* 柔和阴影 */
--shadow-soft: 0 4px 20px rgba(255, 183, 197, 0.15);
--shadow-soft-lg: 0 8px 32px rgba(255, 183, 197, 0.2);

/* 彩色阴影 */
--shadow-pink: 0 4px 20px rgba(255, 183, 197, 0.3);
--shadow-mint: 0 4px 20px rgba(168, 230, 207, 0.3);
--shadow-sky: 0 4px 20px rgba(168, 216, 234, 0.3);

/* 内阴影 */
--shadow-inner-soft: inset 0 2px 8px rgba(0, 0, 0, 0.05);
```

---

## 🧩 组件设计

### 1. 按钮（Button）

#### 主按钮
- 背景：渐变色 (pink → peach)
- 圆角：16px
- 阴影：彩色柔和阴影
- 悬停：上浮 + 光晕扩散
- 图标：可选 emoji 或 Lucide 图标

```tsx
<Button variant="kawaii" size="md">
  ✨ 开始创作
</Button>
```

#### 幽灵按钮
- 边框：2px dashed pastel color
- 背景：透明 → 悬停时淡色背景
- 圆角：16px

#### 图标按钮
- 圆形：48px × 48px
- 背景：glass effect
- 悬停：scale 1.1 + 旋转

### 2. 卡片（Card）

#### 基础卡片
- 背景：glass-white + backdrop-blur
- 边框：1px solid rgba(255,255,255,0.5)
- 圆角：24px
- 阴影：shadow-soft
- 装饰：角落可选小图标/emoji

#### 数据卡片
- 顶部：彩色渐变条 (4px)
- 图标：圆形背景 + emoji
- 数字：渐变色文字

### 3. 输入框（Input）

#### 文本输入
- 背景：--bg-cloud
- 边框：2px solid transparent → focus 时显示 pastel 色
- 圆角：16px
- 前缀图标：可选 emoji
- Focus：外发光效果

#### 搜索框
- 圆角：9999px（胶囊形）
- 阴影：shadow-soft
- 搜索图标：🔍 或自定义 SVG

### 4. 标签（Tag）

```tsx
<Tag color="pink" icon="🌸">可爱</Tag>
<Tag color="mint" icon="🌿">清新</Tag>
<Tag color="sky" icon="☁️">梦幻</Tag>
```

- 圆角：9999px
- 背景：对应颜色的 light 版本
- 边框：1px solid 主色
- 文字：深色版本

---

## 🎬 动画系统

### 入场动画
```css
/* 弹入 */
@keyframes popIn {
  0% { transform: scale(0.8); opacity: 0; }
  70% { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}

/* 滑入 */
@keyframes slideUp {
  0% { transform: translateY(20px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

/* 飘入 */
@keyframes floatIn {
  0% { transform: translateY(30px) rotate(-2deg); opacity: 0; }
  100% { transform: translateY(0) rotate(0); opacity: 1; }
}
```

### 交互动画
```css
/* 按钮点击 */
@keyframes buttonPress {
  0% { transform: scale(1); }
  50% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

/* 悬停上浮 */
.hover-lift {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-soft-lg);
}
```

### 背景动画
```css
/* 云朵飘动 */
@keyframes cloudFloat {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(20px); }
}

/* 星星闪烁 */
@keyframes twinkle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 花瓣飘落 */
@keyframes petalFall {
  0% { transform: translateY(-10px) rotate(0deg); opacity: 1; }
  100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
}
```

---

## 🌈 装饰元素

### 1. 背景装饰
- 漂浮的云朵（SVG）
- 闪烁的星星✨
- 飘落的花瓣🌸
- 渐变光球（blur）

### 2. 图标风格
- 使用 emoji 作为装饰图标
- Lucide 图标保持圆润风格
- 自定义 SVG：云朵、星星、小动物

### 3. 插图元素
- 可爱 mascots（小猫、小兔子）
- 植物装饰（多肉、樱花枝）
- 天气元素（太阳、云朵、彩虹）

---

## 📱 页面布局

### 登录页（Login）
```
┌─────────────────────────────────────┐
│         ☁️      ☁️                  │
│    🌸                              │
│         ✨                         │
│                                     │
│    ┌─────────────────────────┐    │
│    │      🎨 easy-manim      │    │
│    │                         │    │
│    │    [输入 Token]         │    │
│    │                         │    │
│    │    [✨ 开始创作]        │    │
│    │                         │    │
│    │    🐰 可爱 mascots      │    │
│    └─────────────────────────┘    │
│                                     │
│         ☁️              ☁️         │
└─────────────────────────────────────┘
```

### 主页（Studio）
```
┌─────────────────────────────────────┐
│  🌸  easy-manim    [👤] [⚙️]        │
├─────────────────────────────────────┤
│                                     │
│    ┌─────────────────────────┐    │
│    │   🎬 视频预览区          │    │
│    │                         │    │
│    │   [▶️ 播放按钮]          │    │
│    └─────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐  │
│  │  💬 想创作什么动画？          │  │
│  │  [输入框...]        [🚀发送] │  │
│  └─────────────────────────────┘  │
│                                     │
│  [🎨] [📊] [✨] [🌊] 快捷提示      │
│                                     │
└─────────────────────────────────────┘
```

### 任务页（Tasks）
```
┌─────────────────────────────────────┐
│  📝 任务管理    [🔍] [➕]           │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🌸 进行中  │ 🌿 已完成     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🎬 任务名称      [⏳进行中] │   │
│  │  创建时间: 2024-01-01        │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🎬 任务名称      [✅完成]  │   │
│  │  创建时间: 2024-01-01        │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

## 🎨 实现优先级

### Phase 1: 基础样式
- [ ] 色彩系统 CSS 变量
- [ ] 字体系统
- [ ] 基础按钮组件
- [ ] 基础卡片组件

### Phase 2: 组件库
- [ ] 输入框组件
- [ ] 标签组件
- [ ] 图标按钮
- [ ] 加载动画

### Phase 3: 页面重构
- [ ] 登录页重新设计
- [ ] Studio 主界面
- [ ] 任务列表页
- [ ] 视频库页

### Phase 4: 动画效果
- [ ] 背景装饰动画
- [ ] 页面过渡动画
- [ ] 交互动画
- [ ] 加载动画

---

## 📚 参考资源

### 字体
- Google Fonts: Quicksand, Nunito, M PLUS Rounded 1c
- 中文：思源黑体、站酷快乐体

### 图标
- Lucide Icons（圆润版本）
- Fluent Emoji
- Noto Color Emoji

### 设计灵感
- 吉卜力工作室配色
- Kawaii 日本可爱文化
- Soft UI / Glassmorphism
- Pastel Gradients

---

## 💡 特别说明

1. **无障碍**：保持色彩对比度 WCAG 2.1 AA 标准
2. **性能**：动画使用 CSS transforms，避免重排
3. **响应式**：移动端优先，平板/桌面增强
4. **主题**：日间模式为主，夜间模式保持柔和
