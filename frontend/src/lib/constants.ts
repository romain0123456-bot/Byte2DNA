export const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
export const ALLOWED_EXTENSIONS = [".pdf", ".docx"] as const;
export const API_BASE = "/backend";

export const DEFAULT_PARAMS = {
  compression: true,
  includeSha256Export: true,
  ecc: true,
  fragmentLength: 150,
  gcMin: 40,
  gcMax: 60,
  homopolymerMax: 3,
} as const;

export type EncodeParams = {
  compression: boolean;
  includeSha256Export: boolean;
  ecc: boolean;
  fragmentLength: number;
  gcMin: number;
  gcMax: number;
  homopolymerMax: number;
};
