# Easy-Manim 前端全面重构计划

> 目标：系统性重构整个前端代码库，消除Bug、解决逻辑冲突、清理死代码、统一设计规范

## 📊 项目现状分析

### 代码规模
- **TypeScript/TSX 文件**: 50+ 个
- **CSS 文件**: 30+ 个  
- **总代码行数**: ~16,000 行
- **测试覆盖率**: 64 个测试，全部通过

### 已知问题
1. ESLint 警告：28 个（无错误）
2. CSS Keyframes 重复定义：8+
3. 状态管理代码重复：5 处
4. 未使用 CSS 类：可能有少量

---

## 🎯 重构目标

1. **零 Bug**: 消除所有潜在运行时错误
2. **零死代码**: 清理所有未使用的代码
3. **零重复**: 提取公共逻辑到复用模块
4. **统一规范**: 建立一致的代码风格和架构
5. **性能优化**: 减少不必要的重渲染和计算

---

## 📅 重构阶段规划

### Phase 1: 基础设施统一 (第1-2天)

#### 1.1 创建共享 Hooks 库
**优先级**: 🔴 高
**文件**: `src/hooks/useAsyncStatus.ts`, `src/hooks/useForm.ts`, `src/hooks/useToggle.ts`

```typescript
// 目标：统一异步状态管理
// 当前问题：5个页面重复定义 useState<"idle" | "loading" | "error">
// 影响文件：
// - src/features/auth/LoginPageV2.tsx
// - src/features/evals/EvalsPageV2.tsx
// - src/features/memory/MemoryPageV2.tsx
// - src/features/videos/VideosPageV2.tsx
// - src/features/profile/ProfilePageV2.tsx
```

#### 1.2 创建共享工具函数
**优先级**: 🔴 高
**文件**: `src/utils/status.ts`, `src/utils/format.ts`

```typescript
// 目标：统一状态转换和格式化
// - getStatusLabel() 目前分散在 ui.tsx
// - 日期格式化逻辑分散
```

#### 1.3 统一 API 请求层
**优先级**: 🔴 高
**文件**: `src/lib/request.ts`

```typescript
// 目标：统一错误处理和重试逻辑
// 当前：各 API 文件重复 requestJson 逻辑
// 优化：添加请求拦截器、统一错误码处理
```

---

### Phase 2: 组件层重构 (第3-5天)

#### 2.1 基础组件标准化
**优先级**: 🔴 高

| 组件 | 当前问题 | 重构目标 |
|------|---------|---------|
| Button | 变体过多 | 统一为 Kawaii 风格，移除旧变体 |
| Input | ID 生成重复 | 使用 useId hook |
| Toast | 无持久化 | 添加本地存储支持 |
| KawaiiTag | 颜色硬编码 | 使用 design tokens |

#### 2.2 表单组件提取
**优先级**: 🟡 中
**文件**: `src/components/Form/`

```typescript
// 创建可复用表单组件：
// - FormField (标签+输入+错误)
// - FormSelect (带搜索的下拉)
// - FormCheckboxGroup
// - FormRadioGroup
```

#### 2.3 布局组件提取
**优先级**: 🟡 中
**文件**: `src/components/Layout/`

```typescript
// 创建布局组件：
// - PageContainer (统一页面边距、背景)
// - PageHeader (统一标题、面包屑)
// - ContentSection (统一内容区块)
// - EmptyState (统一空状态)
```

---

### Phase 3: 样式系统统一 (第6-7天)

#### 3.1 CSS 变量标准化
**优先级**: 🔴 高
**文件**: `src/styles/variables.css`

```css
/* 目标：合并 tokens.css、ghibli-theme.css、theme-v2.css */
/* 创建单一变量源： */
:root {
  /* Colors */
  --color-primary-50 到 --color-primary-900
  --color-success、--color-warning、--color-error
  
  /* Spacing */
  --space-1 到 --space-12
  
  /* Radius */
  --radius-sm、--radius-md、--radius-lg
  
  /* Shadows */
  --shadow-sm 到 --shadow-xl
  
  /* Animations */
  --ease-kawaii、--duration-fast
}
```

#### 3.2 动画 Keyframes 统一
**优先级**: 🟡 中
**文件**: `src/styles/animations.css`

```css
/* 移除重复的 keyframes */
/* 统一为： */
@keyframes float {}
@keyframes fade-in {}
@keyframes slide-up {}
@keyframes scale-in {}
@keyframes spin {}
```

#### 3.3 CSS Modules 规范化
**优先级**: 🟡 中

```typescript
// 统一命名规范：
// - 组件名: PascalCase.module.css
// - 类名: camelCase
// - 状态类: isActive、isDisabled、hasError
```

---

### Phase 4: 页面层重构 (第8-12天)

#### 4.1 认证模块
**优先级**: 🔴 高
**文件**: `src/features/auth/`

```typescript
// 重构内容：
// 1. 合并 LoginPage.tsx 和 LoginPageV2.tsx
// 2. 删除旧版本 LoginPage.tsx
// 3. 统一表单验证逻辑
// 4. 提取 SessionManager 到独立 hook
```

#### 4.2 Studio 模块
**优先级**: 🔴 高
**文件**: `src/studio/`

```typescript
// 重构内容：
// 1. 合并 store 和 hooks 逻辑
// 2. 优化 VideoStage 组件（减少重渲染）
// 3. 提取 HistoryDrawer 列表项为独立组件
// 4. 优化 SettingsPanel 表单状态管理
```

#### 4.3 Tasks 模块
**优先级**: 🔴 高
**文件**: `src/features/tasks/`

```typescript
// 重构内容：
// 1. 提取 TaskItem、VideoThumb 到 components/
// 2. 优化 StatusBadge 逻辑
// 3. 统一空状态处理
// 4. 清理未使用的 CSS 类
```

#### 4.4 Videos 模块
**优先级**: 🟡 中
**文件**: `src/features/videos/`

```typescript
// 重构内容：
// 1. 优化视频卡片渲染性能
// 2. 提取筛选逻辑到 hook
// 3. 统一分页处理
```

#### 4.5 Profile 模块
**优先级**: 🟡 中
**文件**: `src/features/profile/`

```typescript
// 重构内容：
// 1. 拆分表单为独立组件
// 2. 优化 JSON 编辑器性能
// 3. 清理未使用的 CSS 类
```

#### 4.6 Memory & Evals 模块
**优先级**: 🟢 低
**文件**: `src/features/memory/`, `src/features/evals/`

```typescript
// 重构内容：
// 1. 统一列表渲染逻辑
// 2. 提取公共表格组件
```

---

### Phase 5: 逻辑优化 (第13-15天)

#### 5.1 状态管理优化
**优先级**: 🔴 高

```typescript
// 1. 优化 studioStore：
//    - 拆分大 store 为多个小 store
//    - 使用 selector 减少重渲染
//
// 2. 统一错误处理：
//    - 创建 ErrorBoundary 层级
//    - 统一错误提示样式
//
// 3. 优化加载状态：
//    - 创建 Suspense 边界
//    - 统一 Skeleton 样式
```

#### 5.2 性能优化
**优先级**: 🟡 中

```typescript
// 1. 使用 React.memo 优化：
//    - VideoThumb
//    - TaskItem
//    - HistoryItem
//
// 2. 使用 useMemo 优化：
//    - 筛选排序逻辑
//    - 复杂计算
//
// 3. 使用 useCallback 优化：
//    - 事件处理器
//    - 回调函数传递
```

#### 5.3 无障碍优化
**优先级**: 🟡 中

```typescript
// 1. 统一 ARIA 属性
// 2. 优化键盘导航
// 3. 添加焦点管理
// 4. 支持屏幕阅读器
```

---

### Phase 6: 测试和文档 (第16-18天)

#### 6.1 测试增强
**优先级**: 🟡 中

```typescript
// 1. 添加单元测试：
//    - 所有 hooks
//    - 所有工具函数
//    - 关键业务组件
//
// 2. 添加集成测试：
//    - 用户流程测试
//    - 错误处理测试
//
// 3. 添加视觉回归测试
```

#### 6.2 文档完善
**优先级**: 🟢 低

```typescript
// 1. 组件文档：
//    - Storybook 或类似工具
//    - 组件使用示例
//
// 2. API 文档：
//    - 自动生成 API 文档
//
// 3. 开发规范：
//    - 代码规范文档
//    - 贡献指南
```

---

## 🔧 重构执行清单

### 按模块划分的任务

```
src/
├── components/          [12个文件]  [预计3天]
│   ├── Button/
│   ├── Input/
│   ├── KawaiiIcon/
│   ├── KawaiiTag/
│   ├── Toast/
│   └── [新建] Form/
│   └── [新建] Layout/
│
├── studio/             [20个文件]  [预计4天]
│   ├── components/     [10个文件]
│   ├── hooks/          [5个文件]
│   ├── store/          [2个文件]
│   └── styles/         [8个文件]
│
├── features/           [30个文件]  [预计6天]
│   ├── auth/           [4个文件]
│   ├── tasks/          [6个文件]
│   ├── videos/         [4个文件]
│   ├── profile/        [4个文件]
│   ├── memory/         [4个文件]
│   └── evals/          [4个文件]
│
├── lib/                [8个文件]   [预计2天]
│   ├── api.ts
│   ├── tasksApi.ts
│   ├── videosApi.ts
│   └── [新建] request.ts
│
├── styles/             [5个文件]   [预计2天]
│   ├── variables.css   [合并]
│   ├── animations.css  [新建]
│   └── tokens.css      [保留]
│
└── hooks/              [1个文件]   [预计1天]
    └── [新建] useAsyncStatus.ts
    └── [新建] useForm.ts
```

---

## 📋 质量检查清单

### 每阶段完成检查

- [ ] TypeScript 编译通过
- [ ] ESLint 无错误
- [ ] 所有测试通过
- [ ] 构建成功
- [ ] 手动功能测试通过
- [ ] 性能基准测试通过

### 最终验收标准

- [ ] 代码重复率 < 5%
- [ ] 测试覆盖率 > 80%
- [ ] 零 ESLint 错误
- [ ] 零控制台警告
- [ ] Lighthouse 评分 > 90
- [ ] 包体积减少 > 10%

---

## ⏱️ 时间规划

| 阶段 | 预计时间 | 实际时间 | 状态 |
|------|---------|---------|------|
| Phase 1: 基础设施 | 2天 | - | ⬜ |
| Phase 2: 组件层 | 3天 | - | ⬜ |
| Phase 3: 样式系统 | 2天 | - | ⬜ |
| Phase 4: 页面层 | 5天 | - | ⬜ |
| Phase 5: 逻辑优化 | 3天 | - | ⬜ |
| Phase 6: 测试文档 | 3天 | - | ⬜ |
| **总计** | **18天** | - | ⬜ |

---

## 🚀 并行执行策略

### 工作组划分

**组1: 基础设施组**
- 负责 Phase 1
- 文件: hooks/, lib/, styles/variables.css

**组2: 组件组**
- 负责 Phase 2 + Phase 3
- 文件: components/, styles/

**组3: 页面组**
- 负责 Phase 4
- 文件: features/, studio/

**组4: 优化组**
- 负责 Phase 5 + Phase 6
- 全局优化和测试

### 依赖关系

```
Phase 1 (基础设施)
    ↓
Phase 2 (组件层) ←→ Phase 3 (样式系统)
    ↓
Phase 4 (页面层)
    ↓
Phase 5 (逻辑优化)
    ↓
Phase 6 (测试文档)
```

---

## 📝 风险控制

### 高风险项
1. **状态管理重构** - 可能影响所有页面
2. **CSS 变量统一** - 可能影响视觉表现
3. **API 层重构** - 可能影响数据获取

### 风险缓解
1. 每个重构点创建单独分支
2. 充分测试后再合并
3. 保留回滚方案
4. 分小批次发布

---

## 🎯 成功标准

1. **功能完整**: 所有现有功能正常工作
2. **性能提升**: 首屏加载 < 2s，交互响应 < 100ms
3. **代码质量**: ESLint 0 错误，类型覆盖率 100%
4. **可维护性**: 新增功能开发时间减少 30%
5. **用户体验**: 无明显视觉/交互变化（保持现状）

---

**计划制定**: 2024
**预计完成**: 18个工作日
**负责人**: 前端团队
