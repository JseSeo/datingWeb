import { describe, it, expect, vi, beforeEach } from "vitest";
import { getMyVerification, uploadVerification } from "./api";

beforeEach(() => vi.restoreAllMocks());

describe("verification api", () => {
  it("getMyVerification은 /me/verification GET, null 본문 그대로 반환", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("null", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    const result = await getMyVerification();
    expect(result).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/me/verification"),
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("uploadVerification은 FormData로 POST", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1, user_id: 1, status: "pending",
          reviewed_at: null, created_at: "2026-07-06",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    const file = new File(["x"], "id.jpg", { type: "image/jpeg" });
    const result = await uploadVerification(file);
    expect(result.status).toBe("pending");
    const opts = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(opts.body).toBeInstanceOf(FormData);
    expect(opts.method).toBe("POST");
  });
});
