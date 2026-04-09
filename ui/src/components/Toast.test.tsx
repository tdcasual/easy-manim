import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test } from "vitest";

import { writeLocale } from "../app/locale";
import { ToastProvider } from "./Toast";
import { useToast } from "./useToast";

function ToastTrigger() {
  const { success } = useToast();

  return (
    <button type="button" onClick={() => success("Saved successfully", 10_000)}>
      Show toast
    </button>
  );
}

beforeEach(() => {
  writeLocale("zh-CN");
});

test("toast accessibility labels follow the active locale", async () => {
  writeLocale("en-US");
  const user = userEvent.setup();

  render(
    <ToastProvider>
      <ToastTrigger />
    </ToastProvider>
  );

  await user.click(screen.getByRole("button", { name: /show toast/i }));

  expect(screen.getByRole("region", { name: /notifications/i })).toBeInTheDocument();
  expect(screen.getByText(/Saved successfully/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /close toast/i })).toBeInTheDocument();
});
