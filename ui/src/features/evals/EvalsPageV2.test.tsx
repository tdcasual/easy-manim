import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { EvalsPageV2 } from "./EvalsPageV2";

test("shows an error state instead of an empty state when eval loading fails", async () => {
  writeSessionToken("sess-token-1");

  globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 }));

  render(
    <MemoryRouter>
      <EvalsPageV2 />
    </MemoryRouter>
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/加载评测记录失败/i);
  expect(screen.queryByText(/还没有评测运行/i)).not.toBeInTheDocument();
});
