import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { writeLocale } from "../app/locale";
import { Studio } from "./Studio";

const toggleTheme = vi.fn();
const setPrompt = vi.fn();
const clearError = vi.fn();
const setCurrentTask = vi.fn();
const updateGenerationParams = vi.fn();
const toggleHistory = vi.fn();
const closeHistory = vi.fn();
const toggleSettings = vi.fn();
const closeSettings = vi.fn();
const toggleHelp = vi.fn();
const closeHelp = vi.fn();
const submitTask = vi.fn();
const startPolling = vi.fn();
const cancelCurrentTask = vi.fn();
const loadHistory = vi.fn();

vi.mock("./hooks", () => ({
  useTaskManager: () => ({
    submitTask,
    startPolling,
    cancelCurrentTask,
  }),
  useHistory: () => ({
    historyItems: [],
    loadHistory,
  }),
  useKeyboardShortcuts: () => {},
  useResponsive: () => ({
    isMobile: true,
  }),
}));

vi.mock("./hooks/useTheme", () => ({
  useTheme: () => ({
    isNight: false,
    toggleTheme,
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

vi.mock("./store", () => ({
  useStudioStore: (selector?: (s: unknown) => unknown) => {
    const state = {
      prompt: "",
      setPrompt,
      currentTask: null,
      isGenerating: false,
      error: null,
      isHistoryOpen: false,
      isSettingsOpen: false,
      isHelpOpen: false,
      generationParams: {
        resolution: "720p",
        duration: "10s",
        style: "natural",
        quality: "high",
      },
      toggleHistory,
      closeHistory,
      toggleSettings,
      closeSettings,
      toggleHelp,
      closeHelp,
      clearError,
      setCurrentTask,
      updateGenerationParams,
    };
    return selector ? selector(state) : state;
  },
}));

vi.mock("./components/SkyBackground", () => ({
  SkyBackground: () => <div data-testid="sky-background" />,
}));

vi.mock("./components/HistoryDrawer", () => ({
  HistoryDrawer: () => null,
}));

vi.mock("./components/SettingsPanel", () => ({
  SettingsPanel: () => null,
}));

vi.mock("./components/HelpPanel", () => ({
  HelpPanel: () => null,
}));

beforeEach(() => {
  vi.clearAllMocks();
  writeLocale("en-US");
});

test("studio uses a compact overflow menu for mobile toolbar actions", async () => {
  const user = userEvent.setup();

  render(<Studio />);

  expect(screen.queryByRole("button", { name: /open history/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /open studio actions/i })).toBeInTheDocument();
  expect(screen.getByRole("group", { name: /switch language/i })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /open studio actions/i }));

  expect(await screen.findByRole("dialog", { name: /more actions/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /open history/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /open help/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /open settings/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /switch to night mode/i })).toBeInTheDocument();
});
