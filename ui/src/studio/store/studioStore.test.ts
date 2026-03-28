import { describe, it, expect, beforeEach } from "vitest";
import { useStudioStore, defaultParams } from "./studioStore";

describe("studioStore", () => {
  beforeEach(() => {
    // 重置 store 状态
    useStudioStore.getState().reset();
  });

  describe("prompt", () => {
    it("should update prompt", () => {
      const { setPrompt } = useStudioStore.getState();
      setPrompt("画一个圆球");
      expect(useStudioStore.getState().prompt).toBe("画一个圆球");
    });
  });

  describe("currentTask", () => {
    it("should set current task", () => {
      const { setCurrentTask } = useStudioStore.getState();
      const task = {
        id: "task-1",
        status: "queued" as const,
        title: "测试任务",
      };
      setCurrentTask(task);
      expect(useStudioStore.getState().currentTask).toEqual(task);
    });

    it("should update task status", () => {
      const { setCurrentTask, updateTaskStatus } = useStudioStore.getState();
      setCurrentTask({
        id: "task-1",
        status: "queued",
        title: "测试任务",
      });
      updateTaskStatus("running");
      expect(useStudioStore.getState().currentTask?.status).toBe("running");
    });

    it("should update task with video url", () => {
      const { setCurrentTask, updateTaskStatus } = useStudioStore.getState();
      setCurrentTask({
        id: "task-1",
        status: "running",
        title: "测试任务",
      });
      updateTaskStatus("completed", "https://example.com/video.mp4");
      expect(useStudioStore.getState().currentTask?.status).toBe("completed");
      expect(useStudioStore.getState().currentTask?.videoUrl).toBe("https://example.com/video.mp4");
    });

    it("should not update status when no current task", () => {
      const { updateTaskStatus } = useStudioStore.getState();
      // 不设置 currentTask，直接更新状态
      updateTaskStatus("completed");
      expect(useStudioStore.getState().currentTask).toBeNull();
    });
  });

  describe("isGenerating", () => {
    it("should toggle generating state", () => {
      const { setIsGenerating } = useStudioStore.getState();
      expect(useStudioStore.getState().isGenerating).toBe(false);
      setIsGenerating(true);
      expect(useStudioStore.getState().isGenerating).toBe(true);
    });
  });

  describe("error", () => {
    it("should set error", () => {
      const { setError } = useStudioStore.getState();
      const error = {
        type: "network" as const,
        message: "网络错误",
        retryable: true,
      };
      setError(error);
      expect(useStudioStore.getState().error).toEqual(error);
    });

    it("should clear error", () => {
      const { setError, clearError } = useStudioStore.getState();
      setError({
        type: "network",
        message: "网络错误",
        retryable: true,
      });
      clearError();
      expect(useStudioStore.getState().error).toBeNull();
    });
  });

  describe("panel states", () => {
    describe("history", () => {
      it("should toggle history", () => {
        const { toggleHistory } = useStudioStore.getState();
        expect(useStudioStore.getState().isHistoryOpen).toBe(false);
        toggleHistory();
        expect(useStudioStore.getState().isHistoryOpen).toBe(true);
        toggleHistory();
        expect(useStudioStore.getState().isHistoryOpen).toBe(false);
      });

      it("should close history", () => {
        const { toggleHistory, closeHistory } = useStudioStore.getState();
        toggleHistory();
        expect(useStudioStore.getState().isHistoryOpen).toBe(true);
        closeHistory();
        expect(useStudioStore.getState().isHistoryOpen).toBe(false);
      });
    });

    describe("settings", () => {
      it("should toggle settings", () => {
        const { toggleSettings } = useStudioStore.getState();
        expect(useStudioStore.getState().isSettingsOpen).toBe(false);
        toggleSettings();
        expect(useStudioStore.getState().isSettingsOpen).toBe(true);
      });

      it("should close settings", () => {
        const { toggleSettings, closeSettings } = useStudioStore.getState();
        toggleSettings();
        closeSettings();
        expect(useStudioStore.getState().isSettingsOpen).toBe(false);
      });
    });

    describe("help", () => {
      it("should toggle help", () => {
        const { toggleHelp } = useStudioStore.getState();
        expect(useStudioStore.getState().isHelpOpen).toBe(false);
        toggleHelp();
        expect(useStudioStore.getState().isHelpOpen).toBe(true);
      });

      it("should close help", () => {
        const { toggleHelp, closeHelp } = useStudioStore.getState();
        toggleHelp();
        closeHelp();
        expect(useStudioStore.getState().isHelpOpen).toBe(false);
      });
    });
  });

  describe("generationParams", () => {
    it("should have default params", () => {
      expect(useStudioStore.getState().generationParams).toEqual(defaultParams);
    });

    it("should update single param", () => {
      const { updateGenerationParams } = useStudioStore.getState();
      updateGenerationParams({ resolution: "1080p" });
      expect(useStudioStore.getState().generationParams.resolution).toBe("1080p");
      expect(useStudioStore.getState().generationParams.duration).toBe(defaultParams.duration);
    });

    it("should update multiple params", () => {
      const { updateGenerationParams } = useStudioStore.getState();
      updateGenerationParams({
        resolution: "480p",
        quality: "ultra",
      });
      expect(useStudioStore.getState().generationParams.resolution).toBe("480p");
      expect(useStudioStore.getState().generationParams.quality).toBe("ultra");
    });
  });

  describe("reset", () => {
    it("should reset all state to initial", () => {
      const { setPrompt, setCurrentTask, setError, toggleHistory, reset } =
        useStudioStore.getState();

      // 修改状态
      setPrompt("测试");
      setCurrentTask({ id: "task-1", status: "queued" });
      setError({ type: "network", message: "错误", retryable: true });
      toggleHistory();

      // 验证修改
      expect(useStudioStore.getState().prompt).toBe("测试");
      expect(useStudioStore.getState().currentTask).not.toBeNull();

      // 重置
      reset();

      // 验证重置
      expect(useStudioStore.getState().prompt).toBe("");
      expect(useStudioStore.getState().currentTask).toBeNull();
      expect(useStudioStore.getState().error).toBeNull();
      expect(useStudioStore.getState().isHistoryOpen).toBe(false);
    });

    it("should also reset generationParams on reset", () => {
      const { updateGenerationParams, reset } = useStudioStore.getState();

      updateGenerationParams({ resolution: "1080p" });
      expect(useStudioStore.getState().generationParams.resolution).toBe("1080p");

      reset();

      // reset 会重置所有状态，包括 generationParams
      expect(useStudioStore.getState().generationParams.resolution).toBe(defaultParams.resolution);
    });
  });
});
