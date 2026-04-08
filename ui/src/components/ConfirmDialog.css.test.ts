import confirmDialogStyles from "./ConfirmDialog.css?raw";

test("confirm dialog surfaces use semantic color variables instead of hard-coded rgba", () => {
  expect(confirmDialogStyles).toMatch(/--confirm-dialog-warning-surface:/);
  expect(confirmDialogStyles).not.toMatch(/rgba\(/);
});
