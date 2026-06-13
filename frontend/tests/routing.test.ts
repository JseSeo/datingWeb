import { describe, it, expect } from "vitest";
import { destinationFor } from "../src/lib/routing";

describe("destinationFor", () => {
  it("active → /home", () => {
    expect(destinationFor("active")).toBe("/home");
  });
  it("pending → /pending", () => {
    expect(destinationFor("pending")).toBe("/pending");
  });
});
