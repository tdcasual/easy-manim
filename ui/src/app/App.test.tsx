import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

test("renders the operator console shell", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: /easy-manim console/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /tasks/i })).toBeInTheDocument();
});
