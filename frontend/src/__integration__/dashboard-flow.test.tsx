import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("firecrawl overview flow integration", () => {
  it("redirects root to overview and renders Firecrawl aggregates", async () => {
    window.history.pushState({}, "", "/");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(await screen.findByText("1 / 2 active")).toBeInTheDocument();
    expect(screen.getByText("crawl")).toBeInTheDocument();
  });
});
