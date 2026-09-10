import { describe, expect, it } from "vitest";
import { formatBytes, validateClientFile } from "./fileValidation";

function file(name: string, size = 32, type = "application/pdf") {
  return new File([new Uint8Array(size).fill(1)], name, { type });
}

describe("validateClientFile", () => {
  it("accepte un PDF", () => {
    expect(validateClientFile(file("rapport.pdf")).ok).toBe(true);
  });

  it("accepte un DOCX", () => {
    expect(validateClientFile(file("notes.docx", 64, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")).ok).toBe(true);
  });

  it("rejette une extension incorrecte", () => {
    const result = validateClientFile(file("notes.txt"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBe("Unsupported file type");
  });

  it("rejette un fichier vide", () => {
    const result = validateClientFile(file("vide.pdf", 0));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBe("Empty file");
  });

  it("rejette un fichier trop volumineux", () => {
    const result = validateClientFile(file("gros.pdf", 5 * 1024 * 1024 + 1));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBe("File too large");
  });
});

describe("formatBytes", () => {
  it("affiche des Ko", () => {
    expect(formatBytes(42800)).toContain("Ko");
  });
});
