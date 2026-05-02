import { useI18n } from "../../app/locale";
import { getStatusLabel } from "../../app/ui";
import { Play } from "lucide-react";
import { resolveApiUrl } from "../../lib/api";
import { EmojiIcon, KawaiiIcon } from "../../components";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "../../components/ui/sheet";
import { cn } from "../../lib/utils";

interface HistoryItem {
  id: string;
  title: string;
  status: "completed" | "running" | "rendering" | "queued" | "failed" | "cancelled";
  timestamp: string;
  thumbnailUrl?: string | null;
}

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: HistoryItem[];
  onItemClick: (id: string) => void;
  activeId?: string;
}

const statusConfig = {
  completed: { emoji: "✨", color: "mint" as const },
  rendering: { emoji: "🎨", color: "sky" as const },
  running: { emoji: "🎬", color: "sky" as const },
  queued: { emoji: "⏳", color: "peach" as const },
  failed: { emoji: "💥", color: "pink" as const },
  cancelled: { emoji: "🚫", color: "lemon" as const },
};

function resolveThumbnailUrl(url: string | null | undefined): string | null {
  const resolved = resolveApiUrl(url);
  if (!resolved) return null;

  try {
    const parsed = new URL(resolved, window.location.origin);
    return ["http:", "https:"].includes(parsed.protocol) ? resolved : null;
  } catch {
    return null;
  }
}

export function HistoryDrawer({
  isOpen,
  onClose,
  items,
  onItemClick,
  activeId,
}: HistoryDrawerProps) {
  const { locale, t } = useI18n();

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        closeLabel={t("studio.history.close")}
        closeAutoFocus
        className="w-full max-w-sm border-l border-cloud-200 bg-white p-0 dark:border-cloud-800 dark:bg-cloud-900"
      >
        <SheetHeader className="border-b border-cloud-200 p-5 dark:border-cloud-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-pink-100">
              <EmojiIcon emoji="📚" color="pink" size="sm" />
            </div>
            <div className="flex flex-col">
              <SheetTitle className="text-base font-semibold text-foreground">
                {t("studio.history.title")}
              </SheetTitle>
              <SheetDescription className="text-xs text-muted-foreground">
                🎨 {t("studio.history.count", { count: items.length })}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div
          className="flex-1 overflow-y-auto p-4"
          role="list"
          aria-label={t("studio.history.list")}
        >
          {items.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-lavender-100">
                <EmojiIcon emoji="📖" color="lavender" size="xl" bounce />
              </div>
              <p className="text-sm font-medium text-foreground">
                {t("studio.history.emptyTitle")}
              </p>
              <p className="text-xs text-muted-foreground">{t("studio.history.emptySubtitle")}</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {items.map((item, index) => {
                const status = statusConfig[item.status] ?? {
                  emoji: "📹",
                  color: "lavender" as const,
                };
                const statusLabel = getStatusLabel(item.status, locale);
                const isActive = item.id === activeId;
                const thumbnailUrl = resolveThumbnailUrl(item.thumbnailUrl);

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onItemClick(item.id)}
                    role="listitem"
                    aria-current={isActive ? "true" : undefined}
                    aria-label={`${item.title}, ${statusLabel}, ${item.timestamp}`}
                    className={cn(
                      "flex items-center gap-3 rounded-2xl border p-3 text-left transition-colors transition-transform transition-shadow",
                      isActive
                        ? "border-pink-300 bg-pink-50/60 shadow-sm"
                        : "border-cloud-200 bg-cloud-50 hover:-translate-y-0.5 hover:bg-white hover:shadow-sm dark:border-cloud-800 dark:bg-cloud-800 dark:hover:bg-cloud-700"
                    )}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    {thumbnailUrl ? (
                      <div
                        className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl"
                        aria-hidden="true"
                      >
                        <img
                          className="h-full w-full object-cover"
                          src={thumbnailUrl}
                          alt=""
                          loading="lazy"
                          decoding="async"
                        />
                      </div>
                    ) : (
                      <div
                        className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-pink-300 to-lavender-300"
                        aria-hidden="true"
                      >
                        <KawaiiIcon icon={Play} color="white" size="xs" />
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <EmojiIcon emoji={status.emoji} color={status.color} size="xs" />
                          {statusLabel}
                        </span>
                        <span>·</span>
                        <span>{item.timestamp}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
