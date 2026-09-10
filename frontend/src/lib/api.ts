import { API_BASE } from "./constants";
import type { EncodeParams } from "./constants";
import type { ApiError, EncodeResponse } from "./types";

function errorMessage(payload: ApiError | string, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (typeof payload === "object" && payload) {
    if (typeof payload.error === "string") return payload.error;
    if (typeof payload.detail === "string") return payload.detail;
  }
  return fallback;
}

export async function encodeFile(
  file: File,
  params: EncodeParams,
): Promise<EncodeResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append("compression", String(params.compression));
  body.append("include_sha256_export", String(params.includeSha256Export));
  body.append("ecc", String(params.ecc));
  body.append("fragment_length", String(params.fragmentLength));
  body.append("gc_min", String(params.gcMin));
  body.append("gc_max", String(params.gcMax));
  body.append("homopolymer_max", String(params.homopolymerMax));

  const response = await fetch(`${API_BASE}/api/encode`, {
    method: "POST",
    body,
  });
  const payload = (await response.json().catch(() => ({}))) as ApiError;
  if (!response.ok) {
    throw new Error(errorMessage(payload, "Encoding failed"));
  }
  return payload as EncodeResponse;
}

export async function downloadXlsx(resultId: string, suggestedName: string): Promise<void> {
  let response = await fetch(`${API_BASE}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result_id: resultId }),
  });

  if (!response.ok) {
    const getResp = await fetch(
      `${API_BASE}/api/export?result_id=${encodeURIComponent(resultId)}`,
    ).catch(() => null);
    if (getResp && getResp.ok) {
      response = getResp;
    } else {
      const payload = (await response.json().catch(() => ({}))) as ApiError;
      throw new Error(errorMessage(payload, "Export failed"));
    }
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.style.display = "none";
  link.href = url;
  const header = response.headers.get("content-disposition");
  const match = header?.match(/filename="?([^";]+)"?/);
  const filename = match?.[1]?.replace(/['"]/g, "").trim() || suggestedName;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  setTimeout(() => {
    try {
      document.body.removeChild(link);
    } catch {
      // ignore if removed
    }
    window.URL.revokeObjectURL(url);
  }, 1500);
}
