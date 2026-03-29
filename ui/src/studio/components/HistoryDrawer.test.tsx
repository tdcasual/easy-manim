import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { writeLocale } from "../../app/locale";
import { HistoryDrawer } from "./HistoryDrawer";

function HistoryDrawerHarness() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        打开历史
      </button>
      <button type="button">背景按钮</button>
      <HistoryDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onItemClick={() => {}}
        items={[
          {
            id: "task-1",
            title: "蓝色圆形片头",
            status: "completed",
            timestamp: "刚刚",
            thumbnailUrl: "/api/tasks/task-1/artifacts/previews/frame_001.png",
          },
        ]}
      />
    </>
  );
}

test("history drawer renders relative thumbnails and restores trigger focus on close", async () => {
  const user = userEvent.setup();
  const { container } = render(<HistoryDrawerHarness />);

  const trigger = screen.getByRole("button", { name: "打开历史" });
  trigger.focus();

  await user.click(trigger);

  const closeButton = await screen.findByRole("button", { name: "关闭历史抽屉" });
  expect(closeButton).toHaveFocus();

  expect(container.querySelector('img[src*="frame_001.png"]')).not.toBeNull();

  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

test("history drawer uses the active locale for dialog copy", () => {
  writeLocale("en-US");

  render(
    <HistoryDrawer
      isOpen={true}
      onClose={() => {}}
      onItemClick={() => {}}
      items={[
        {
          id: "task-1",
          title: "Blue circle intro",
          status: "completed",
          timestamp: "just now",
          thumbnailUrl: null,
        },
      ]}
    />
  );

  expect(screen.getByRole("heading", { name: /creation history/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /close history drawer/i })).toBeInTheDocument();
  expect(screen.getByText(/1 creations?/i)).toBeInTheDocument();
  expect(screen.getByText(/completed/i)).toBeInTheDocument();
});

test("history drawer renders cancelled items without crashing", () => {
  writeLocale("en-US");

  render(
    <HistoryDrawer
      isOpen={true}
      onClose={() => {}}
      onItemClick={() => {}}
      items={[
        {
          id: "task-2",
          title: "Cancelled draft",
          status: "cancelled",
          timestamp: "2 minutes ago",
          thumbnailUrl: null,
        },
      ]}
    />
  );

  expect(screen.getByText(/^Cancelled$/i)).toBeInTheDocument();
  expect(
    screen.getByRole("listitem", { name: /cancelled draft, cancelled, 2 minutes ago/i })
  ).toBeInTheDocument();
});
