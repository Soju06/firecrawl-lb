import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("firecrawl settings flow integration", () => {
  it("loads runtime settings and password management", async () => {
    window.history.pushState({}, "", "/settings");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(await screen.findByText("/tmp/firecrawl-lb")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Password" })).toBeInTheDocument();
  });
});
