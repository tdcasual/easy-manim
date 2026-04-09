import { Toaster as SonnerToaster, toast } from "sonner";

import { useTheme } from "../../studio/hooks/useTheme";

function Toaster() {
  const { isNight } = useTheme();
  return (
    <SonnerToaster
      position="top-center"
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "group toast flex w-full items-center gap-3 rounded-2xl border border-border bg-card/90 p-4 shadow-lg backdrop-blur-md",
          title: "text-sm font-medium text-foreground",
          description: "text-xs text-muted-foreground",
          actionButton:
            "inline-flex h-8 items-center justify-center rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground",
          cancelButton:
            "inline-flex h-8 items-center justify-center rounded-lg bg-muted px-3 text-xs font-medium text-muted-foreground",
          error: "border-destructive/30 text-destructive",
          success: "border-mint-500/30 text-mint-600",
          warning: "border-peach-500/30 text-peach-600",
          info: "border-sky-500/30 text-sky-600",
        },
      }}
      theme={isNight ? "dark" : "light"}
    />
  );
}

export { toast, Toaster };
