import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("firecrawl jobs flow integration", () => {
  it("loads the jobs page and renders persisted crawl jobs", async () => {
    window.history.pushState({}, "", "/jobs");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Jobs" })).toBeInTheDocument();
    expect(await screen.findByText("crawl-1")).toBeInTheDocument();
    expect(screen.getByText("submitted")).toBeInTheDocument();
  });
});
