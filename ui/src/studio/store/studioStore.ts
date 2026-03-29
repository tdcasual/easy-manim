/**
 * Studio Store - 使用 Zustand 管理全局状态
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface GenerationParams {
  resolution: "480p" | "720p" | "1080p";
  duration: "5s" | "10s" | "15s";
  style: "natural" | "vivid" | "anime" | "cinematic";
  quality: "standard" | "high" | "ultra";
}

export interface Task {
  id: string;
  videoUrl?: string | null;
  title?: string;
  status: "queued" | "running" | "rendering" | "completed" | "failed" | "cancelled";
}

export interface TaskError {
  type: "network" | "generation" | "timeout" | "unknown";
  message: string;
  retryable: boolean;
}

interface StudioState {
  // 输入状态
  prompt: string;
  setPrompt: (prompt: string) => void;

  // 任务状态
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
  updateTaskStatus: (status: Task["status"], videoUrl?: string) => void;

  // 生成状态
  isGenerating: boolean;
  setIsGenerating: (value: boolean) => void;

  // 错误状态
  error: TaskError | null;
  setError: (error: TaskError | null) => void;
  clearError: () => void;

  // 面板状态
  isHistoryOpen: boolean;
  toggleHistory: () => void;
  closeHistory: () => void;

  isSettingsOpen: boolean;
  toggleSettings: () => void;
  closeSettings: () => void;

  isHelpOpen: boolean;
  toggleHelp: () => void;
  closeHelp: () => void;

  // 生成参数
  generationParams: GenerationParams;
  updateGenerationParams: (params: Partial<GenerationParams>) => void;

  // 重置
  reset: () => void;
}

export const defaultParams: GenerationParams = {
  resolution: "720p",
  duration: "10s",
  style: "natural",
  quality: "high",
};

const initialState = {
  prompt: "",
  currentTask: null as Task | null,
  isGenerating: false,
  error: null as TaskError | null,
  isHistoryOpen: false,
  isSettingsOpen: false,
  isHelpOpen: false,
  // 创建新的对象，避免引用 defaultParams
  generationParams: { ...defaultParams },
};

export const useStudioStore = create<StudioState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // 输入
      setPrompt: (prompt) => set({ prompt }),

      // 任务
      setCurrentTask: (task) => set({ currentTask: task }),
      updateTaskStatus: (status, videoUrl) => {
        const { currentTask } = get();
        if (currentTask) {
          set({
            currentTask: { ...currentTask, status, videoUrl: videoUrl ?? currentTask.videoUrl },
          });
        }
      },

      // 生成状态
      setIsGenerating: (isGenerating) => set({ isGenerating }),

      // 错误
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      // 面板 - 切换时自动关闭其他面板，防止冲突
      toggleHistory: () =>
        set((state) => ({
          isHistoryOpen: !state.isHistoryOpen,
          isSettingsOpen: state.isHistoryOpen ? state.isSettingsOpen : false,
          isHelpOpen: state.isHistoryOpen ? state.isHelpOpen : false,
        })),
      closeHistory: () => set({ isHistoryOpen: false }),

      toggleSettings: () =>
        set((state) => ({
          isSettingsOpen: !state.isSettingsOpen,
          isHistoryOpen: state.isSettingsOpen ? state.isHistoryOpen : false,
          isHelpOpen: state.isSettingsOpen ? state.isHelpOpen : false,
        })),
      closeSettings: () => set({ isSettingsOpen: false }),

      toggleHelp: () =>
        set((state) => ({
          isHelpOpen: !state.isHelpOpen,
          isHistoryOpen: state.isHelpOpen ? state.isHistoryOpen : false,
          isSettingsOpen: state.isHelpOpen ? state.isSettingsOpen : false,
        })),
      closeHelp: () => set({ isHelpOpen: false }),

      // 参数
      updateGenerationParams: (params) =>
        set((state) => ({
          generationParams: { ...state.generationParams, ...params },
        })),

      // 重置
      reset: () => set(initialState),
    }),
    {
      name: "studio-storage",
      partialize: (state) => ({
        generationParams: state.generationParams,
      }),
    }
  )
);
