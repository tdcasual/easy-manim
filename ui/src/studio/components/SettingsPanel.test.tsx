import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { writeLocale } from "../../app/locale";
import { SettingsPanel, type GenerationParams } from "./SettingsPanel";

function SettingsPanelHarness() {
  const [isOpen, setIsOpen] = useState(false);
  const [params, setParams] = useState<GenerationParams>({
    resolution: "720p" as const,
    duration: "10s" as const,
    style: "natural" as const,
    quality: "high" as const,
  });

  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        打开设置
      </button>
      <button type="button">背景按钮</button>
      <SettingsPanel
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        params={params}
        onParamsChange={setParams}
      />
    </>
  );
}

test("settings panel traps focus and restores it to the trigger when closed", async () => {
  const user = userEvent.setup();

  render(<SettingsPanelHarness />);

  const trigger = screen.getByRole("button", { name: "打开设置" });
  trigger.focus();

  await user.click(trigger);

  const closeButton = await screen.findByRole("button", { name: "关闭设置" });
  expect(closeButton).toHaveFocus();

  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog", { name: "生成参数设置" })).not.toBeInTheDocument();
});

test("settings panel uses the active locale for headings and options", () => {
  writeLocale("en-US");

  render(
    <SettingsPanel
      isOpen={true}
      onClose={() => {}}
      params={{
        resolution: "720p",
        duration: "10s",
        style: "natural",
        quality: "high",
      }}
      onParamsChange={() => {}}
    />
  );

  expect(screen.getByRole("dialog", { name: /generation settings/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /generation settings/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /resolution/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /video duration/i })).toBeInTheDocument();
  expect(screen.getByText(/balanced speed and quality/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /close settings/i })).toBeInTheDocument();
});
