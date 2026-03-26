import { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import "./ErrorBoundary.css";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onReset?.();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary" role="alert">
          <div className="error-boundary__icon">
            <AlertCircle size={48} />
          </div>
          <h2 className="error-boundary__title">出错了</h2>
          <p className="error-boundary__message">
            {this.state.error?.message || "发生了意外错误"}
          </p>
          <button
            className="error-boundary__button"
            onClick={this.handleReset}
            type="button"
          >
            <RefreshCw size={18} />
            重试
          </button>
          {import.meta.env.DEV && this.state.errorInfo && (
            <details className="error-boundary__details">
              <summary>错误详情</summary>
              <pre>{this.state.errorInfo.componentStack}</pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// 简单的错误 fallback 组件
export function ErrorFallback({
  error,
  resetError,
}: {
  error: Error;
  resetError: () => void;
}) {
  return (
    <div className="error-fallback" role="alert">
      <AlertCircle size={32} />
      <h3>加载失败</h3>
      <p>{error.message}</p>
      <button onClick={resetError} type="button">
        重试
      </button>
    </div>
  );
}
