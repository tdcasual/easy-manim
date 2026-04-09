import { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { readLocale, translate } from "../app/locale";

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
        <div
          className="flex min-h-[400px] flex-col items-center justify-center rounded-2xl border border-destructive/25 bg-gradient-to-b from-destructive/5 to-destructive/[0.02] p-8 text-center shadow-sm"
          role="alert"
        >
          <div className="mb-4 animate-pulse-glow text-destructive">
            <AlertCircle size={48} />
          </div>
          <h2 className="mb-2 text-2xl font-bold text-foreground">
            {translate(readLocale(), "errorBoundary.title")}
          </h2>
          <p className="mb-6 max-w-md text-sm text-muted-foreground">
            {this.state.error?.message ?? translate(readLocale(), "errorBoundary.message")}
          </p>
          <button
            className="flex items-center gap-2 rounded-xl border border-border bg-muted/60 px-5 py-2.5 text-sm font-medium text-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:bg-muted"
            onClick={this.handleReset}
            type="button"
          >
            <RefreshCw size={18} />
            {translate(readLocale(), "errorBoundary.retry")}
          </button>
          {import.meta.env.DEV && this.state.errorInfo && (
            <details className="mt-6 w-full max-w-xl">
              <summary className="cursor-pointer p-2 text-sm text-muted-foreground">
                {translate(readLocale(), "errorBoundary.details")}
              </summary>
              <pre className="mt-2 max-h-[300px] overflow-auto rounded-xl bg-black/10 p-4 text-left text-xs text-secondary-foreground">
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export function ErrorFallback({ error, resetError }: { error: Error; resetError: () => void }) {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-xl border border-destructive/25 bg-destructive/10 p-6 text-center text-destructive"
      role="alert"
    >
      <AlertCircle size={32} />
      <h3 className="text-base font-semibold text-foreground">
        {translate(readLocale(), "errorFallback.title")}
      </h3>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <button
        onClick={resetError}
        type="button"
        className="rounded-lg border border-border bg-muted/60 px-4 py-2 text-sm font-medium text-foreground transition-all hover:bg-muted"
      >
        {translate(readLocale(), "errorBoundary.retry")}
      </button>
    </div>
  );
}
