import type { ReactNode } from "react";

type PageIntroProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  aside?: ReactNode;
};

type SectionPanelProps = {
  title: string;
  detail?: string;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
};

type StatusPillProps = {
  value: string;
  compact?: boolean;
};

type MetricChipProps = {
  label: string;
  value: ReactNode;
};

type EmptyStateProps = {
  title: string;
  body: string;
  action?: ReactNode;
};

type JsonBlockProps = {
  value: unknown;
};

function joinClasses(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

function normalizeStatus(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

const STATUS_LABELS: Record<string, string> = {
  active: "启用中",
  applied: "已应用",
  cancelled: "已取消",
  completed: "已完成",
  dismissed: "已忽略",
  failed: "失败",
  pending: "待处理",
  queued: "排队中",
  rendering: "渲染中",
  review: "待复核",
  running: "执行中",
};

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

export function PageIntro({ eyebrow, title, description, actions, aside }: PageIntroProps) {
  return (
    <header className="pageIntro">
      <div className="pageIntroMain">
        <p className="pageEyebrow">{eyebrow}</p>
        <div className="pageIntroHeading">
          <h2>{title}</h2>
          {actions ? <div className="pageIntroActions">{actions}</div> : null}
        </div>
        <p className="pageLead">{description}</p>
      </div>
      {aside ? <div className="pageIntroAside">{aside}</div> : null}
    </header>
  );
}

export function SectionPanel({ title, detail, actions, className, children }: SectionPanelProps) {
  return (
    <section className={joinClasses("sectionPanel", className)}>
      <div className="panelHeader">
        <div>
          <div className="panelTitle">{title}</div>
          {detail ? <p className="panelDetail">{detail}</p> : null}
        </div>
        {actions ? <div className="panelActions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function StatusPill({ value, compact = false }: StatusPillProps) {
  const normalized = normalizeStatus(value);
  return (
    <span className={joinClasses("statusPill", `statusPill--${normalized}`, compact && "statusPill--compact")}>
      {STATUS_LABELS[normalized] ?? value}
    </span>
  );
}

export function getStatusLabel(value: string): string {
  const normalized = normalizeStatus(value);
  return STATUS_LABELS[normalized] ?? value;
}

export function MetricChip({ label, value }: MetricChipProps) {
  return (
    <div className="metricChip">
      <span className="metricChipLabel">{label}</span>
      <strong className="metricChipValue">{value}</strong>
    </div>
  );
}

export function EmptyState({ title, body, action }: EmptyStateProps) {
  return (
    <div className="emptyState">
      <div>
        <div className="emptyStateTitle">{title}</div>
        <p className="emptyStateBody">{body}</p>
      </div>
      {action ? <div className="emptyStateAction">{action}</div> : null}
    </div>
  );
}

export function JsonBlock({ value }: JsonBlockProps) {
  return <pre className="jsonBlock">{safeStringify(value)}</pre>;
}
