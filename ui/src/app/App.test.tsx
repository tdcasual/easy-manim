import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

test("renders the operator console shell", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: /easy-manim/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /登录/i })).toBeInTheDocument();
});
