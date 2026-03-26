import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { JsonBlock, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import { EvalRunSummary, getEval } from "../../lib/evalsApi";
import { useSession } from "../auth/useSession";

function safeSuccessRate(report?: Record<string, unknown>): string {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? `${Math.round(raw * 100)}%` : "—";
}

export function EvalDetailPage() {
  const { runId } = useParams();
  const { sessionToken } = useSession();
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !sessionToken) return;
    let cancelled = false;
    setError(null);
    getEval(runId, sessionToken)
      .then((nextRun) => {
        if (cancelled) return;
        setRun(nextRun);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "eval_load_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [runId, sessionToken]);

  if (!runId) {
    return (
      <section className="page">
        <h2>评测详情</h2>
        <p className="muted">缺少运行 ID。</p>
      </section>
    );
  }

  if (!sessionToken) {
    return (
      <section className="page">
        <h2>评测详情</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="page">
        <h2>评测详情</h2>
        <p className="muted">加载失败：{error}</p>
      </section>
    );
  }

  if (!run) {
    return (
      <section className="page">
        <h2>评测详情</h2>
        <p className="muted">正在加载…</p>
      </section>
    );
  }

  const cases = Array.isArray(run.items) ? run.items : [];

  return (
    <section className="page page--detail">
      <PageIntro
        eyebrow="评测运行"
        title="评测详情"
        description="查看用例结果、识别需要人工复核的热点，并在同一控制台里快速判断本轮质量表现。"
        actions={
          <Link className="button buttonQuiet" to="/evals">
            返回评测列表
          </Link>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="套件" value={run.suite_id} />
            <MetricChip label="用例数" value={run.total_cases} />
            <MetricChip label="通过率" value={safeSuccessRate(run.report)} />
          </div>
        }
      />

      <div className="identityBand">
        <div>
          <span className="muted small">运行 ID</span>
          <div className="identityCode">{run.run_id}</div>
        </div>
        <div className="identityBandMeta">
          <span className="muted small">提供方</span>
          <p>{run.provider}</p>
        </div>
      </div>

      <div className="pageSplit">
        <SectionPanel title="用例结果" detail="逐条查看本轮评测中的用例结果、人工复核标记和问题码。">
          {cases.length ? (
            <ul className="listStack">
              {cases.map((item) => {
                const quality = typeof item.quality_score === "number" ? item.quality_score.toFixed(2) : "—";
                const duration = typeof item.duration_seconds === "number" ? `${item.duration_seconds.toFixed(1)}s` : "—";
                const issueCodes = Array.isArray(item.issue_codes) && item.issue_codes.length ? item.issue_codes.join(", ") : "无";

                return (
                  <li key={`${item.task_id}:${item.root_task_id}`} className="listStaticRow">
                    <div className="listPrimary">
                      <div className="listTitleRow">
                        <span className="listTitle">{item.task_id}</span>
                        <div className="inlineStatusRow">
                          {item.manual_review_required ? <StatusPill value="review" compact /> : null}
                          <StatusPill value={item.status} compact />
                        </div>
                      </div>
                      <p className="listCaption">问题码：{issueCodes}</p>
                    </div>
                    <div className="listMeta listMeta--column">
                      <span className="muted small">{duration}</span>
                      <span className="muted small">质量分：{quality}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="muted">这次运行里暂时没有可显示的用例结果。</p>
          )}
        </SectionPanel>

        <SectionPanel title="评测报告" detail="当前评测运行返回的原始报告载荷。">
          <JsonBlock value={run.report ?? {}} />
        </SectionPanel>
      </div>
    </section>
  );
}
