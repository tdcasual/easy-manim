import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { writeLocale } from "../app/locale";
import { useStudioStore } from "./store";
import { Studio } from "./Studio";

const loadHistory = vi.fn();

vi.mock("./hooks", () => ({
  useTaskManager: () => ({
    submitTask: vi.fn(),
    startPolling: vi.fn(),
    cancelCurrentTask: vi.fn(),
  }),
  useHistory: () => ({
    historyItems: [
      {
        id: "task-1",
        title: "Blue sphere intro",
        status: "completed",
        timestamp: "just now",
        thumbnailUrl: "/artifacts/previews/frame_001.png",
        videoUrl: "/artifacts/videos/final.mp4",
      },
    ],
    loadHistory,
  }),
  useKeyboardShortcuts: () => {},
  useResponsive: () => ({
    isMobile: false,
  }),
}));

vi.mock("./hooks/useTheme", () => ({
  useTheme: () => ({
    isNight: false,
    toggleTheme: vi.fn(),
  }),
}));

vi.mock("../features/auth/useSession", () => ({
  useSession: () => ({
    sessionToken: "sess-token-1",
    isAuthenticated: true,
  }),
}));

vi.mock("../components/AuthModal", () => ({
  AuthModal: () => null,
  useAuthGuard: () => ({
    showAuthModal: false,
    closeAuthModal: vi.fn(),
  }),
}));

vi.mock("./components/SkyBackground", () => ({
  SkyBackground: () => <div data-testid="sky-background" />,
}));

vi.mock("./components/VideoStage", () => ({
  VideoStage: ({ videoUrl }: { videoUrl?: string | null }) => (
    <div data-testid="video-stage">{videoUrl ?? "no-video"}</div>
  ),
}));

vi.mock("./components/HistoryDrawer", () => ({
  HistoryDrawer: ({ onItemClick }: { onItemClick: (id: string) => void }) => (
    <button type="button" onClick={() => onItemClick("task-1")}>
      choose history item
    </button>
  ),
}));

vi.mock("./components/SettingsPanel", () => ({
  SettingsPanel: () => null,
}));

vi.mock("./components/HelpPanel", () => ({
  HelpPanel: () => null,
}));

beforeEach(() => {
  vi.clearAllMocks();
  useStudioStore.getState().reset();
  writeLocale("en-US");
});

test("selecting a history item restores the playable video instead of its preview image", async () => {
  const user = userEvent.setup();

  render(<Studio />);

  expect(screen.getByTestId("video-stage")).toHaveTextContent("no-video");

  await user.click(screen.getByRole("button", { name: /choose history item/i }));

  expect(screen.getByTestId("video-stage")).toHaveTextContent("/artifacts/videos/final.mp4");
});
