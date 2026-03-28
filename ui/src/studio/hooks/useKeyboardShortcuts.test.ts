import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useKeyboardShortcuts } from "./useKeyboardShortcuts";

describe("useKeyboardShortcuts", () => {
  const mockCallbacks = {
    onToggleSettings: vi.fn(),
    onToggleHistory: vi.fn(),
    onToggleHelp: vi.fn(),
    onToggleTheme: vi.fn(),
    onFocusInput: vi.fn(),
  };

  const defaultOptions = {
    isSettingsOpen: false,
    isHistoryOpen: false,
    isHelpOpen: false,
    ...mockCallbacks,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // 清理事件监听器
    document.removeEventListener("keydown", expect.any(Function));
  });

  it("should register keydown event listener", () => {
    const addEventListenerSpy = vi.spyOn(document, "addEventListener");
    renderHook(() => useKeyboardShortcuts(defaultOptions));
    expect(addEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));
  });

  it("should call onToggleHelp when ? is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "?" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHelp).toHaveBeenCalledTimes(1);
  });

  it("should call onFocusInput when / is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "/" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onFocusInput).toHaveBeenCalledTimes(1);
  });

  it("should call onToggleHistory when H is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "h" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).toHaveBeenCalledTimes(1);
  });

  it("should call onToggleHistory when uppercase H is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "H" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).toHaveBeenCalledTimes(1);
  });

  it("should call onToggleSettings when S is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "s" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleSettings).toHaveBeenCalledTimes(1);
  });

  it("should call onToggleTheme when T is pressed", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "t" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleTheme).toHaveBeenCalledTimes(1);
  });

  it("should not trigger shortcuts when help is open", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        ...defaultOptions,
        isHelpOpen: true,
      })
    );

    const event = new KeyboardEvent("keydown", { key: "h" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).not.toHaveBeenCalled();
  });

  it("should not trigger shortcuts when input is focused", () => {
    // 创建一个输入框并聚焦
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();

    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", {
      key: "h",
      bubbles: true,
    });
    Object.defineProperty(event, "target", { value: input, enumerable: true });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it("should blur input when Escape is pressed in input", () => {
    const input = document.createElement("input");
    input.id = "test-input";
    document.body.appendChild(input);
    input.focus();

    const blurSpy = vi.spyOn(input, "blur");

    renderHook(() => useKeyboardShortcuts(defaultOptions));

    // 创建一个 KeyboardEvent，目标设为 input
    const event = new KeyboardEvent("keydown", {
      key: "Escape",
      bubbles: true,
    });
    Object.defineProperty(event, "target", { value: input, enumerable: true });

    document.dispatchEvent(event);

    expect(blurSpy).toHaveBeenCalledTimes(1);

    document.body.removeChild(input);
  });

  it("should call onToggleSettings when Escape is pressed and settings is open", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        ...defaultOptions,
        isSettingsOpen: true,
      })
    );

    const event = new KeyboardEvent("keydown", { key: "Escape" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleSettings).toHaveBeenCalledTimes(1);
  });

  it("should call onToggleHistory when Escape is pressed and history is open", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        ...defaultOptions,
        isHistoryOpen: true,
      })
    );

    const event = new KeyboardEvent("keydown", { key: "Escape" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).toHaveBeenCalledTimes(1);
  });

  it("should not trigger H when settings is open", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        ...defaultOptions,
        isSettingsOpen: true,
      })
    );

    const event = new KeyboardEvent("keydown", { key: "h" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHistory).not.toHaveBeenCalled();
  });

  it("should not trigger S when history is open", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        ...defaultOptions,
        isHistoryOpen: true,
      })
    );

    const event = new KeyboardEvent("keydown", { key: "s" });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleSettings).not.toHaveBeenCalled();
  });

  it("should ignore ctrl+? combination", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "?", ctrlKey: true });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHelp).not.toHaveBeenCalled();
  });

  it("should ignore meta+? combination", () => {
    renderHook(() => useKeyboardShortcuts(defaultOptions));

    const event = new KeyboardEvent("keydown", { key: "?", metaKey: true });
    document.dispatchEvent(event);

    expect(mockCallbacks.onToggleHelp).not.toHaveBeenCalled();
  });
});
