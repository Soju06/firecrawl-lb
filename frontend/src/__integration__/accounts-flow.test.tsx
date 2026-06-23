import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("firecrawl accounts flow integration", () => {
  it("loads Firecrawl accounts and keeps credential secrets hidden", async () => {
    window.history.pushState({}, "", "/accounts");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Accounts" })).toBeInTheDocument();
    expect(await screen.findAllByText("Primary Firecrawl")).toHaveLength(2);
    expect(screen.getAllByText("Secondary Firecrawl")).toHaveLength(2);
    expect(screen.queryByText(/api_key/i)).not.toBeInTheDocument();
  });
});
