import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "../../app/App";
import { clearSessionToken, writeSessionToken } from "../../lib/session";

test("unauthenticated access to protected routes renders login page", () => {
  clearSessionToken();

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument();
});

test("authenticated access to protected routes renders the requested page", () => {
  writeSessionToken("sess-token-1");

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByRole("heading", { name: /^tasks$/i })).toBeInTheDocument();
});
