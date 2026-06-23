import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("firecrawl logs flow integration", () => {
  it("loads request logs for sync Firecrawl endpoints", async () => {
    window.history.pushState({}, "", "/logs");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Logs" })).toBeInTheDocument();
    expect(await screen.findByText("scrape")).toBeInTheDocument();
    expect(screen.getByText("123 ms")).toBeInTheDocument();
  });
});
