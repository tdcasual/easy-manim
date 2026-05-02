/**
 * Studio store - global state managed by Zustand.
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
  // Input state
  prompt: string;
  setPrompt: (prompt: string) => void;

  // Task state
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
  updateTaskStatus: (status: Task["status"], videoUrl?: string) => void;

  // Generation state
  isGenerating: boolean;
  setIsGenerating: (value: boolean) => void;

  // Error state
  error: TaskError | null;
  setError: (error: TaskError | null) => void;
  clearError: () => void;

  // Panel state
  isHistoryOpen: boolean;
  toggleHistory: () => void;
  closeHistory: () => void;

  isSettingsOpen: boolean;
  toggleSettings: () => void;
  closeSettings: () => void;

  isHelpOpen: boolean;
  toggleHelp: () => void;
  closeHelp: () => void;

  // Generation params
  generationParams: GenerationParams;
  updateGenerationParams: (params: Partial<GenerationParams>) => void;

  // Reset
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
  // Create a new object to avoid referencing defaultParams
  generationParams: { ...defaultParams },
};

export const useStudioStore = create<StudioState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Input
      setPrompt: (prompt) => set({ prompt }),

      // Task
      setCurrentTask: (task) => set({ currentTask: task }),
      updateTaskStatus: (status, videoUrl) => {
        const { currentTask } = get();
        if (currentTask) {
          set({
            currentTask: { ...currentTask, status, videoUrl: videoUrl ?? currentTask.videoUrl },
          });
        }
      },

      // Generation state
      setIsGenerating: (isGenerating) => set({ isGenerating }),

      // Error
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      // Panels - auto-close others when toggling to avoid conflicts
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

      // Params
      updateGenerationParams: (params) =>
        set((state) => ({
          generationParams: { ...state.generationParams, ...params },
        })),

      // Reset
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
