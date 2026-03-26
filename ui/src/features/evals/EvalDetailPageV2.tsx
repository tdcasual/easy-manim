import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BarChart3, Loader2, Clock, AlertCircle, ClipboardList, CheckCircle2 } from "lucide-react";
import { useSession } from "../auth/useSession";
import { EvalRunSummary, getEval } from "../../lib/evalsApi";
import { SkeletonCard } from "../../components/Skeleton";
import "./EvalDetailPageV2.css";

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function readSuccessRate(report?: Record<string, unknown>): number | null {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function EvalDetailPageV2() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useSession();
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    if (!runId || !sessionToken) return;
    getEval(runId, sessionToken)
      .then(setRun)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"));
  }, [runId, sessionToken]);
  
  if (!runId) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">缺少运行 ID</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">加载失败: {error}</div>
      </div>
    );
  }
  
  if (!run) {
    return (
      <div className="page-v2">
        <div className="page-header-v2">
          <SkeletonCard />
        </div>
        <div className="eval-detail-header">
          <SkeletonCard />
        </div>
        <div className="section-card-v2">
          <SkeletonCard />
        </div>
      </div>
    );
  }
  
  const cases = Array.isArray(run.items) ? run.items : [];
  const successRate = readSuccessRate(run.report);
  
  return (
    <div className="page-v2">
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <button onClick={() => navigate(-1)} className="back-link">
            <ArrowLeft size={18} />
            返回
          </button>
          <h1 className="page-title-v2">评测详情</h1>
          <p className="page-description-v2">{run.run_id}</p>
        </div>
      </div>
      
      <div className="eval-detail-header">
        <div className="eval-detail-stats">
          <div className="eval-stat">
            <span className="stat-label">套件</span>
            <span className="stat-value">{run.suite_id}</span>
          </div>
          <div className="eval-stat">
            <span className="stat-label">用例数</span>
            <span className="stat-value">{run.total_cases}</span>
          </div>
          <div className="eval-stat">
            <span className="stat-label">通过率</span>
            <span className={`stat-value ${successRate && successRate >= 0.8 ? 'success' : successRate && successRate >= 0.5 ? 'warning' : 'error'}`}>
              {formatPercent(successRate)}
            </span>
          </div>
        </div>
      </div>
      
      <div className="section-card-v2">
        <div className="section-header-v2">
          <h3 className="section-title-v2">
            <BarChart3 size={20} />
            用例结果
          </h3>
        </div>
        
        <div className="case-list">
          {cases.length > 0 ? (
            cases.map((item) => {
              const quality = typeof item.quality_score === "number" ? item.quality_score.toFixed(2) : "—";
              const duration = typeof item.duration_seconds === "number" ? `${item.duration_seconds.toFixed(1)}s` : "—";
              const issueCodes = Array.isArray(item.issue_codes) && item.issue_codes.length 
                ? item.issue_codes.join(", ") 
                : "无";
              
              return (
                <div key={`${item.task_id}:${item.root_task_id}`} className="case-item">
                  <div className="case-header">
                    <span className="case-id">{item.task_id}</span>
                    <div className="case-badges">
                      {item.manual_review_required && (
                        <span className="case-badge review">
                          <AlertCircle size={12} />
                          待复核
                        </span>
                      )}
                      <span className={`case-badge ${item.status.toLowerCase()}`}>
                        {item.status}
                      </span>
                    </div>
                  </div>
                  <div className="case-details">
                    <div className="case-stat">
                      <Clock size={14} />
                      {duration}
                    </div>
                    <div className="case-stat">
                      质量分: {quality}
                    </div>
                    <div className="case-issues">
                      问题: {issueCodes}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty-state-v2 case-empty">
              <ClipboardList size={48} />
              <p>暂无用例数据</p>
              <span>该评测运行尚未生成详细结果</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
