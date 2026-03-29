import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { writeLocale } from "../../app/locale";
import { listTasks } from "../../lib/tasksApi";
import { listRecentVideos } from "../../lib/videosApi";
import { useHistory } from "./useHistory";

vi.mock("../../lib/tasksApi", () => ({
  listTasks: vi.fn(),
}));

vi.mock("../../lib/videosApi", () => ({
  listRecentVideos: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
  writeLocale("zh-CN");
});

test("history items preserve the playable video url separately from the preview thumbnail", async () => {
  vi.mocked(listTasks).mockResolvedValue({
    items: [
      {
        task_id: "task-1",
        status: "completed",
        display_title: "Blue sphere intro",
      },
    ],
  });

  vi.mocked(listRecentVideos).mockResolvedValue({
    items: [
      {
        task_id: "task-1",
        display_title: "Blue sphere intro",
        status: "completed",
        updated_at: "2026-03-28T00:00:00Z",
        latest_preview_url: "/artifacts/previews/frame_001.png",
        latest_video_url: "/artifacts/videos/final.mp4",
      },
    ],
  });

  const { result } = renderHook(() => useHistory({ sessionToken: "sess-token-1" }));

  await act(async () => {
    await result.current.loadHistory();
  });

  await waitFor(() => {
    expect(result.current.historyItems).toHaveLength(1);
  });

  expect(result.current.historyItems[0]).toMatchObject({
    thumbnailUrl: "/artifacts/previews/frame_001.png",
  });
  expect((result.current.historyItems[0] as any).videoUrl).toBe("/artifacts/videos/final.mp4");
});

test("history item timestamps follow the active locale", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-03-28T00:02:00Z"));
  writeLocale("en-US");

  vi.mocked(listTasks).mockResolvedValue({
    items: [
      {
        task_id: "task-2",
        status: "completed",
        display_title: "Ocean intro",
      },
    ],
  });

  vi.mocked(listRecentVideos).mockResolvedValue({
    items: [
      {
        task_id: "task-2",
        display_title: "Ocean intro",
        status: "completed",
        updated_at: "2026-03-28T00:00:00Z",
        latest_preview_url: null,
        latest_video_url: "/artifacts/videos/ocean.mp4",
      },
    ],
  });

  const { result } = renderHook(() => useHistory({ sessionToken: "sess-token-1" }));

  await act(async () => {
    await result.current.loadHistory();
  });

  expect(result.current.historyItems).toHaveLength(1);
  expect(result.current.historyItems[0].timestamp).toBe("2 minutes ago");
});
