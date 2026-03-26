function normalizeStatus(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

const STATUS_LABELS: Record<string, string> = {
  active: "启用中",
  applied: "已应用",
  cancelled: "已取消",
  completed: "已完成",
  disabled: "已停用",
  dismissed: "已忽略",
  failed: "失败",
  pending: "待处理",
  queued: "排队中",
  rendering: "渲染中",
  review: "待复核",
  running: "执行中",
};

export function getStatusLabel(value: string): string {
  const normalized = normalizeStatus(value);
  return STATUS_LABELS[normalized] ?? value;
}
