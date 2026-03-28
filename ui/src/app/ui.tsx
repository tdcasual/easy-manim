import { Locale, readLocale } from "./locale";

function normalizeStatus(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

const STATUS_LABELS: Record<Locale, Record<string, string>> = {
  "zh-CN": {
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
  },
  "en-US": {
    active: "Active",
    applied: "Applied",
    cancelled: "Cancelled",
    completed: "Completed",
    disabled: "Disabled",
    dismissed: "Dismissed",
    failed: "Failed",
    pending: "Pending",
    queued: "Queued",
    rendering: "Rendering",
    review: "Needs review",
    running: "Running",
  },
};

export function getStatusLabel(value: string, locale: Locale = readLocale()): string {
  const normalized = normalizeStatus(value);
  return STATUS_LABELS[locale][normalized] ?? value;
}
