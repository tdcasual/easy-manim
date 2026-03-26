import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import { EvalRunSummary, listEvals } from "../../lib/evalsApi";
import { useSession } from "../auth/useSession";

function readSuccessRate(report?: Record<string, unknown>): number | null {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function EvalsPage() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<EvalRunSummary[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const response = await listEvals(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "evals_load_failed");
    }
  }

  useEffect(() => {
    refresh();
    // refresh is stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  if (!sessionToken) {
    return (
      <section className="page">
        <h2>评测</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  const rates = items.map((item) => readSuccessRate(item.report)).filter((value): value is number => value !== null);
  const averageSuccess = rates.length ? rates.reduce((sum, value) => sum + value, 0) / rates.length : null;

  return (
    <section className="page">
      <PageIntro
        eyebrow="验证"
        title="评测"
        description="查看智能体范围内的评测运行，比较套件结果，并识别画像是在帮助质量稳定还是开始偏移。"
        actions={
          <button className="button buttonQuiet" type="button" onClick={refresh} disabled={status === "loading"}>
            {status === "loading" ? "正在刷新…" : "刷新"}
          </button>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="运行次数" value={items.length} />
            <MetricChip label="平均通过率" value={formatPercent(averageSuccess)} />
            <MetricChip label="可见用例" value={items.reduce((sum, item) => sum + item.total_cases, 0)} />
          </div>
        }
      />

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "evals_load_failed"}
        </p>
      ) : null}

      <SectionPanel title="最近运行" detail="每次评测都只显示当前智能体可见的数据，并可进入更细的用例拆解。">
        {status === "loading" && items.length === 0 ? <p className="muted">正在加载…</p> : null}

        {items.length ? (
          <ul className="listStack" aria-label="eval run list">
            {items.map((run) => {
              const rate = readSuccessRate(run.report);
              return (
                <li key={run.run_id}>
                  <Link className="listLinkRow" to={`/evals/${encodeURIComponent(run.run_id)}`}>
                    <div className="listPrimary">
                      <div className="listTitleRow">
                        <span className="listTitle">{run.run_id}</span>
                        <StatusPill value={rate === null ? `${run.total_cases} 个用例` : formatPercent(rate)} compact />
                      </div>
                      <p className="listCaption">
                        {run.suite_id} · {run.provider}
                      </p>
                    </div>
                    <div className="listMeta">
                      <span className="muted small">{run.total_cases} 个用例</span>
                      <span className="listChevron" aria-hidden="true">
                        ↗
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : status === "loading" ? null : (
          <EmptyState title="还没有评测运行" body="先执行一次评测套件，然后再回到这里比较结果并查看具体用例表现。" />
        )}
      </SectionPanel>
    </section>
  );
}
