import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { BarChart3, RefreshCw, Loader2, ArrowRight, CheckCircle2, XCircle, ClipboardList } from "lucide-react";
import { useSession } from "../auth/useSession";
import { EvalRunSummary, listEvals } from "../../lib/evalsApi";
import { SkeletonMetricCard, SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import "./EvalsPageV2.css";

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function readSuccessRate(report?: Record<string, unknown>): number | null {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function EvalsPageV2() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<EvalRunSummary[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  
  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    setStatus("loading");
    try {
      const response = await listEvals(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
      announcePolite(`已加载 ${response.items?.length || 0} 条评测记录`);
    } catch {
      setStatus("error");
      announcePolite("加载评测记录失败");
    }
  }, [sessionToken, announcePolite]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  const rates = items.map(item => readSuccessRate(item.report)).filter((v): v is number => v !== null);
  const averageSuccess = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : null;
  
  if (!sessionToken) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">当前未登录</div>
      </div>
    );
  }
  
  return (
    <div className="page-v2">
      <ARIALiveRegion />
      
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">验证</div>
          <h1 className="page-title-v2">评测</h1>
          <p className="page-description-v2">
            查看智能体范围内的评测运行，比较套件结果
          </p>
        </div>
        <button 
          className="refresh-btn"
          onClick={refresh}
          disabled={status === "loading"}
        >
          {status === "loading" ? (
            <Loader2 size={18} className="spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          刷新
        </button>
      </div>
      
      {status === "loading" && items.length === 0 ? (
        <div className="metrics-grid-v2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : (
        <div className="metrics-grid-v2">
          <div className="metric-card-v2" style={{ '--card-color': 'var(--accent-purple)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(139, 92, 246, 0.15)', color: 'var(--accent-purple)' }}>
              <BarChart3 size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">运行次数</p>
              <h3 className="metric-value-v2">{items.length}</h3>
            </div>
          </div>
          <div className="metric-card-v2" style={{ '--card-color': 'var(--success)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' }}>
              <CheckCircle2 size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">平均通过率</p>
              <h3 className="metric-value-v2">{formatPercent(averageSuccess)}</h3>
            </div>
          </div>
          <div className="metric-card-v2" style={{ '--card-color': 'var(--accent-cyan)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(0, 212, 255, 0.15)', color: 'var(--accent-cyan)' }}>
              <BarChart3 size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">可见用例</p>
              <h3 className="metric-value-v2">{items.reduce((sum, item) => sum + item.total_cases, 0)}</h3>
            </div>
          </div>
        </div>
      )}
      
      <div className="section-card-v2">
        <div className="section-header-v2">
          <h3 className="section-title-v2">
            <BarChart3 size={20} />
            最近运行
          </h3>
        </div>
        
        <div className="eval-list">
          {status === "loading" && items.length === 0 ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : items.length > 0 ? (
            items.map((run, index) => {
              const rate = readSuccessRate(run.report);
              return (
                <Link 
                  key={run.run_id}
                  to={`/evals/${encodeURIComponent(run.run_id)}`}
                  className="eval-row"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="eval-info">
                    <div className="eval-id">{run.run_id}</div>
                    <div className="eval-meta">
                      {run.suite_id} · {run.provider}
                    </div>
                  </div>
                  <div className="eval-stats">
                    <div className="eval-rate">
                      {rate !== null ? (
                        <>
                          {rate >= 0.8 ? (
                            <CheckCircle2 size={16} color="#10b981" />
                          ) : rate >= 0.5 ? (
                            <BarChart3 size={16} color="#f59e0b" />
                          ) : (
                            <XCircle size={16} color="#ef4444" />
                          )}
                          {formatPercent(rate)}
                        </>
                      ) : (
                        "—"
                      )}
                    </div>
                    <div className="eval-cases">{run.total_cases} 个用例</div>
                  </div>
                  <ArrowRight size={16} className="eval-arrow" />
                </Link>
              );
            })
          ) : (
            <div className="empty-state-v2 eval-empty">
              <ClipboardList size={48} />
              <p>还没有评测运行</p>
              <span>评测运行后将在此显示结果</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
