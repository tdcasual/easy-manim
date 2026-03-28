import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { useConfirm } from "./useConfirm";

function ConfirmDialogHarness() {
  const { confirm, ConfirmDialog } = useConfirm();

  return (
    <>
      <button
        type="button"
        onClick={() => {
          void confirm({
            title: "确认操作",
            message: "确认后会继续执行。",
            confirmText: "确认执行",
            cancelText: "稍后再说",
          });
        }}
      >
        打开确认框
      </button>
      <button type="button">背景按钮</button>
      <ConfirmDialog />
    </>
  );
}

test("keeps keyboard focus inside the confirm dialog and restores trigger focus on close", async () => {
  const user = userEvent.setup();

  render(<ConfirmDialogHarness />);

  const trigger = screen.getByRole("button", { name: "打开确认框" });
  trigger.focus();

  await user.click(trigger);

  const confirmButton = await screen.findByRole("button", { name: "确认执行" });
  expect(confirmButton).toHaveFocus();

  await user.tab();
  expect(screen.getByRole("button", { name: "关闭" })).toHaveFocus();

  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
