import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { writeLocale } from "../../app/locale";
import { clearSessionToken } from "../../lib/session";
import { AuthModal } from "./AuthModal";

beforeEach(() => {
  clearSessionToken();
});

test("auth modal moves focus inside and restores the mini trigger on close", async () => {
  const user = userEvent.setup();

  render(
    <>
      <button type="button">背景按钮</button>
      <AuthModal />
    </>
  );

  const trigger = screen.getByRole("button", { name: "点击登录" });
  trigger.focus();

  await user.click(trigger);

  const dialog = await screen.findByRole("dialog", { name: /登录/ });
  const tokenInput = screen.getByLabelText(/智能体令牌/);
  expect(dialog).toContainElement(document.activeElement as HTMLElement | SVGElement | null);
  expect(tokenInput).toHaveFocus();

  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog", { name: /登录/ })).not.toBeInTheDocument();
  const restoredTrigger = screen.getByRole("button", { name: "点击登录" });
  expect(restoredTrigger).toHaveFocus();
});

test("auth modal follows the active locale", async () => {
  const user = userEvent.setup();
  writeLocale("en-US");

  render(<AuthModal />);

  const trigger = screen.getByRole("button", { name: /open login/i });

  await user.click(trigger);

  expect(await screen.findByRole("dialog", { name: /log in/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/agent token/i)).toBeInTheDocument();
  expect(screen.getByText(/no token\?/i)).toBeInTheDocument();
});
