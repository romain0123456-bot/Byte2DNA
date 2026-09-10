import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES } from "./constants";

export type FileValidation =
  | { ok: true; extension: string }
  | { ok: false; error: string };

export function validateClientFile(file: File | null): FileValidation {
  if (!file) {
    return { ok: false, error: "Empty file" };
  }
  if (file.size <= 0) {
    return { ok: false, error: "Empty file" };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { ok: false, error: "File too large" };
  }
  const name = file.name.toLowerCase();
  const extension = ALLOWED_EXTENSIONS.find((ext) => name.endsWith(ext));
  if (!extension) {
    return { ok: false, error: "Unsupported file type" };
  }
  return { ok: true, extension };
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} o`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} Ko`;
  return `${(size / (1024 * 1024)).toFixed(2)} Mo`;
}

export async function sha256File(file: File): Promise<string> {
  const buffer = await readAsArrayBuffer(file);
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function readAsArrayBuffer(file: Blob): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === "function") {
    try {
      return await file.arrayBuffer();
    } catch {
      // jsdom / test File objects can expose a non-functional arrayBuffer
    }
  }
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });
}
