import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getMyVerification,
  uploadVerification,
  listPendingVerifications,
  reviewVerification,
  fetchVerificationImage,
  ApiError,
} from "./api";

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

  it("listPendingVerifications는 /admin/verifications GET", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 1, user_id: 2, status: "pending", reviewed_at: null,
            created_at: "2026-07-06", name: "김학생", university: "연세대학교" },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const result = await listPendingVerifications();
    expect(result[0].name).toBe("김학생");
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/verifications"),
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("reviewVerification은 action 본문으로 POST", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ id: 1, user_id: 2, status: "approved", reviewed_at: null,
          created_at: "2026-07-06", name: "김학생", university: "연세대학교" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const result = await reviewVerification(1, "approve");
    expect(result.status).toBe("approved");
    const opts = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body as string)).toEqual({ action: "approve" });
  });

  it("fetchVerificationImage는 blob을 objectURL로 변환", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob([new Uint8Array([1, 2, 3])]), { status: 200 }),
    );
    const createSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    const url = await fetchVerificationImage(7);
    expect(url).toBe("blob:mock-url");
    expect(createSpy).toHaveBeenCalledOnce();
  });

  it("fetchVerificationImage는 실패 시 ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 404 }));
    await expect(fetchVerificationImage(9)).rejects.toBeInstanceOf(ApiError);
  });
});
