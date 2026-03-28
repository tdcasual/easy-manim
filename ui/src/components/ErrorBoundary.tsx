import { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { readLocale, translate } from "../app/locale";
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
          <h2 className="error-boundary__title">
            {translate(readLocale(), "errorBoundary.title")}
          </h2>
          <p className="error-boundary__message">
            {this.state.error?.message ?? translate(readLocale(), "errorBoundary.message")}
          </p>
          <button className="error-boundary__button" onClick={this.handleReset} type="button">
            <RefreshCw size={18} />
            {translate(readLocale(), "errorBoundary.retry")}
          </button>
          {import.meta.env.DEV && this.state.errorInfo && (
            <details className="error-boundary__details">
              <summary>{translate(readLocale(), "errorBoundary.details")}</summary>
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
export function ErrorFallback({ error, resetError }: { error: Error; resetError: () => void }) {
  return (
    <div className="error-fallback" role="alert">
      <AlertCircle size={32} />
      <h3>{translate(readLocale(), "errorFallback.title")}</h3>
      <p>{error.message}</p>
      <button onClick={resetError} type="button">
        {translate(readLocale(), "errorBoundary.retry")}
      </button>
    </div>
  );
}
