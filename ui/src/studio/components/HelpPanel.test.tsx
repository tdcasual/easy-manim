import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { writeLocale } from "../../app/locale";
import { HelpPanel } from "./HelpPanel";

function HelpPanelHarness() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        打开帮助
      </button>
      <button type="button">背景按钮</button>
      <HelpPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}

test("help panel traps focus and restores it to the trigger when closed", async () => {
  const user = userEvent.setup();

  render(<HelpPanelHarness />);

  const trigger = screen.getByRole("button", { name: "打开帮助" });
  trigger.focus();

  await user.click(trigger);

  const closeButton = await screen.findByRole("button", { name: "关闭帮助" });
  expect(closeButton).toHaveFocus();

  await user.tab();
  expect(closeButton).toHaveFocus();

  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog", { name: "快捷键帮助" })).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

test("help panel uses the active locale for shortcut descriptions", () => {
  writeLocale("en-US");

  render(<HelpPanel isOpen={true} onClose={() => {}} />);

  expect(screen.getByRole("dialog", { name: /keyboard shortcuts/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /keyboard shortcuts/i })).toBeInTheDocument();
  expect(screen.getByText(/focus the prompt/i)).toBeInTheDocument();
  expect(screen.getByText(/show or hide help/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /close help/i })).toBeInTheDocument();
});
