import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useStudioStore } from "./store";
import { useResponsive } from "./hooks/useResponsive";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";

describe("Studio Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store
    useStudioStore.getState().reset();
  });

  it("should have correct initial store state", () => {
    const state = useStudioStore.getState();

    expect(state.prompt).toBe("");
    expect(state.currentTask).toBeNull();
    expect(state.isGenerating).toBe(false);
    expect(state.error).toBeNull();
    expect(state.isHistoryOpen).toBe(false);
    expect(state.isSettingsOpen).toBe(false);
    expect(state.isHelpOpen).toBe(false);
  });

  it("should update prompt correctly", () => {
    const { setPrompt } = useStudioStore.getState();

    setPrompt("画一个圆球");

    expect(useStudioStore.getState().prompt).toBe("画一个圆球");
  });

  it("should toggle panels correctly", () => {
    const { toggleHistory, toggleSettings, toggleHelp, closeHistory, closeSettings } =
      useStudioStore.getState();

    // Toggle history
    toggleHistory();
    expect(useStudioStore.getState().isHistoryOpen).toBe(true);
    expect(useStudioStore.getState().isSettingsOpen).toBe(false);

    // Close history and toggle settings
    closeHistory();
    toggleSettings();
    expect(useStudioStore.getState().isHistoryOpen).toBe(false);
    expect(useStudioStore.getState().isSettingsOpen).toBe(true);

    // Close settings and toggle help
    closeSettings();
    toggleHelp();
    expect(useStudioStore.getState().isSettingsOpen).toBe(false);
    expect(useStudioStore.getState().isHelpOpen).toBe(true);
  });
});

describe("useResponsive Integration", () => {
  it("should return correct breakpoint values", () => {
    const { result } = renderHook(() => useResponsive());

    expect(result.current.breakpoint).toBeDefined();
    expect(result.current.isMobile).toBeDefined();
    expect(result.current.isDesktop).toBeDefined();
    expect(result.current.width).toBeGreaterThan(0);
  });
});

describe("useKeyboardShortcuts Integration", () => {
  const mockCallbacks = {
    isSettingsOpen: false,
    isHistoryOpen: false,
    isHelpOpen: false,
    onToggleSettings: vi.fn(),
    onToggleHistory: vi.fn(),
    onToggleHelp: vi.fn(),
    onToggleTheme: vi.fn(),
    onFocusInput: vi.fn(),
  };

  it("should register keyboard shortcuts", () => {
    const addEventListenerSpy = vi.spyOn(document, "addEventListener");

    renderHook(() => useKeyboardShortcuts(mockCallbacks));

    expect(addEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

    addEventListenerSpy.mockRestore();
  });
});
