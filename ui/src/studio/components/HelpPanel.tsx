import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  const { t } = useI18n();
  const shortcuts = [
    { key: "/", description: t("studio.help.shortcuts.focusPrompt"), emoji: "🔍" },
    { key: "Enter", description: t("studio.help.shortcuts.submit"), emoji: "🚀" },
    { key: "Shift + Enter", description: t("studio.help.shortcuts.newline"), emoji: "↩️" },
    { key: "Esc", description: t("studio.help.shortcuts.escape"), emoji: "🚪" },
    { key: "H", description: t("studio.help.shortcuts.history"), emoji: "📚" },
    { key: "S", description: t("studio.help.shortcuts.settings"), emoji: "⚙️" },
    { key: "T", description: t("studio.help.shortcuts.theme"), emoji: "🌓" },
    { key: "?", description: t("studio.help.shortcuts.help"), emoji: "❓" },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        closeLabel={t("studio.help.close")}
        closeAutoFocus
        className="rounded-3xl border-cloud-200 bg-white p-0 shadow-xl dark:border-cloud-800 dark:bg-cloud-900 sm:max-w-md"
      >
        <DialogHeader className="border-b border-cloud-200 p-5 dark:border-cloud-800">
          <div className="flex items-center gap-2">
            <EmojiIcon emoji="⌨️" color="sky" size="sm" />
            <DialogTitle className="text-lg font-semibold text-foreground">
              {t("studio.help.title")}
            </DialogTitle>
          </div>
          <DialogDescription className="sr-only">{t("studio.help.footer")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-1 p-5">
          {shortcuts.map((shortcut) => (
            <div
              key={shortcut.key}
              className="flex items-center justify-between rounded-xl px-3 py-2 transition-colors hover:bg-cloud-50"
            >
              <div className="flex items-center gap-2 text-sm text-foreground">
                <EmojiIcon emoji={shortcut.emoji} color="white" size="xs" />
                <span>{shortcut.description}</span>
              </div>
              <kbd className="rounded-lg border border-cloud-200 bg-cloud-50 px-2 py-1 text-xs font-semibold text-cloud-700 dark:border-cloud-800 dark:bg-cloud-800">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="border-t border-cloud-200 p-4 text-center text-xs text-muted-foreground dark:border-cloud-800">
          💡 {t("studio.help.footer")}
        </div>
      </DialogContent>
    </Dialog>
  );
}
