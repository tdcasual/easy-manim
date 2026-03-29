import { render, screen } from "@testing-library/react";
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
    isMobile: false,
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
  useStudioStore: () => ({
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
  }),
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
  writeLocale("zh-CN");
});

test("studio surfaces follow the active locale after login", () => {
  writeLocale("en-US");

  render(<Studio />);

  expect(screen.getByRole("group", { name: /switch language/i })).toBeInTheDocument();
  expect(screen.getByText(/AI animation studio/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /open history/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /switch to night mode/i })).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/describe the animation you want/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /animate a blue sphere/i })).toBeInTheDocument();
  expect(screen.getByText(/start your creative journey/i)).toBeInTheDocument();
});
