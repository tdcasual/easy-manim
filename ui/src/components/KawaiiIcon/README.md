# KawaiiIcon - 二次元风格图标组件

## 简介

KawaiiIcon 为 Lucide 图标添加了可爱的二次元包装，包括彩色圆形背景、弹性动画和 emoji 支持。

## 组件

### KawaiiIcon

为 Lucide 图标添加彩色背景容器。

```tsx
import { KawaiiIcon } from "@/components";
import { Sparkles, Heart } from "lucide-react";

// 基础用法
<KawaiiIcon icon={Sparkles} />

// 自定义颜色和大小
<KawaiiIcon icon={Heart} color="pink" size="lg" />

// 添加动画
<KawaiiIcon icon={Sparkles} pulse />
<KawaiiIcon icon={Heart} bounce />
<KawaiiIcon icon={Star} rotate />

// 可点击
<KawaiiIcon icon={Heart} onClick={() => console.log("clicked")} />
```

### EmojiIcon

使用 emoji 作为图标，同样支持彩色背景和动画。

```tsx
import { EmojiIcon } from "@/components";

// 基础用法
<EmojiIcon emoji="🌸" />

// 自定义样式
<EmojiIcon emoji="✨" color="lemon" size="xl" bounce />
<EmojiIcon emoji="🎀" color="pink" pulse />
```

### StatusIcon

预设的状态图标，使用 emoji 表示不同状态。

```tsx
import { StatusIcon } from "@/components";

<StatusIcon status="success" />  // ✨
<StatusIcon status="error" />    // 💥
<StatusIcon status="warning" />  // ⚠️
<StatusIcon status="info" />     // 💡
<StatusIcon status="loading" />  // 🌀 (带动画)
```

### KawaiiIconButton

可点击的图标按钮。

```tsx
import { KawaiiIconButton } from "@/components";
import { X } from "lucide-react";

<KawaiiIconButton
  icon={X}
  color="pink"
  size="md"
  ariaLabel="关闭"
  onClick={() => console.log("closed")}
/>
```

## 颜色选项

- `pink` - 樱花粉 🌸
- `mint` - 薄荷绿 🌿
- `sky` - 天空蓝 ☁️
- `lavender` - 薰衣草紫 🪻
- `peach` - 蜜桃橙 🍑
- `lemon` - 柠檬黄 🍋
- `white` - 纯白（带阴影）
- `gradient` - 粉彩渐变 🌈

## 尺寸选项

- `xs` - 24px
- `sm` - 32px
- `md` - 40px（默认）
- `lg` - 52px
- `xl` - 64px

## 最佳实践

1. **装饰性图标**：使用 `EmojiIcon` 替代纯文字装饰
2. **功能图标**：使用 `KawaiiIcon` 保持界面一致性
3. **状态提示**：使用 `StatusIcon` 提供清晰的状态反馈
4. **动画使用**：不要过度使用动画，`pulse` 适合加载状态，`bounce` 适合装饰

## 示例场景

```tsx
// 登录页装饰
<EmojiIcon emoji="☁️" color="pink" size="lg" bounce />
<EmojiIcon emoji="⭐" color="lemon" size="sm" pulse />

// 功能按钮
<KawaiiIcon icon={Settings} color="mint" onClick={openSettings} />

// 状态提示
<StatusIcon status="success" size="md" />
```
