import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "../app/page";
import type { EncodeResponse } from "./types";

const digestMock = vi.fn(async () => new Uint8Array(32).fill(9).buffer);
Object.defineProperty(globalThis, "crypto", {
  configurable: true,
  value: { subtle: { digest: digestMock } },
});

const passResponse: EncodeResponse = {
  encoding_version: "BYTE2DNA-POC-1",
  result_id: "abc123def456",
  file: {
    original_filename: "document-test.pdf",
    original_extension: "pdf",
    original_size: 42,
    sha256_original: "aa".repeat(32),
  },
  stats: {
    fragment_count: 3,
    total_nucleotides: 450,
    gc_average: 49.8,
    gc_min_observed: 41.2,
    gc_max_observed: 58.7,
    max_homopolymer_observed: 3,
    original_size: 42,
    compressed_size: 31,
    compression_ratio: 0.74,
    compression: true,
    fragments_valid: 3,
    fragments_warning: 0,
    fragments_invalid: 0,
  },
  roundtrip: {
    result: "PASS",
    sha256_original: "aa".repeat(32),
    sha256_reconstructed: "aa".repeat(32),
    reconstructed_size: 42,
    message: "Fichier reconstruit bit-à-bit",
    bit_identical: true,
  },
  fragments_preview: [
    {
      fragment_id: "DNA000001",
      index: 0,
      sequence: "ACGT".repeat(37) + "AC",
      length_nt: 150,
      gc_percent: 49.3,
      max_homopolymer: 2,
      encoding_variant: 3,
      ecc: true,
      status: "VALID",
    },
  ],
  fragment_count: 3,
  synthesis_review_required: false,
  export_allowed: true,
  export_warning: null,
  qc_message: "ENCODING VALID / SYNTHESIS CONSTRAINTS PASS",
  profile: "Generic POC",
};

describe("Byte2DNA page", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    digestMock.mockClear();
  });

  it("affiche le titre, les paramètres et un export désactivé avant validation", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Byte2DNA" })).toBeInTheDocument();
    expect(screen.getByText("Du fichier à la séquence ADN")).toBeInTheDocument();
    expect(screen.getByText("Compression")).toBeInTheDocument();
    expect(screen.getByText("SHA-256 export")).toBeInTheDocument();
    expect(screen.getByLabelText("Longueur fragment")).toHaveValue("150");
    expect(screen.queryByTestId("export-button")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Générer et valider/ })).toBeDisabled();
  });

  it("importe un PDF, affiche le SHA-256, lance l'encodage et active l'export après PASS", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => passResponse,
      }),
    );
    render(<HomePage />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const pdf = new File([new Uint8Array([37, 80, 68, 70, 45])], "document-test.pdf", {
      type: "application/pdf",
    });
    await user.upload(input, pdf);
    await waitFor(() => expect(screen.getByTestId("file-meta")).toHaveTextContent("document-test.pdf"));
    expect(screen.getByTestId("file-meta")).toHaveTextContent("Type : PDF");
    await waitFor(() =>
      expect(screen.getByTestId("file-meta").textContent).toMatch(/SHA-256 : [0-9a-f]{64}/),
    );

    await user.click(screen.getByRole("button", { name: /Générer et valider/ }));
    await waitFor(() => expect(screen.getByTestId("roundtrip")).toHaveTextContent("ROUND-TRIP : PASS"));
    expect(screen.getByTestId("results")).toHaveTextContent("✓ Fichier reconstruit bit-à-bit");
    expect(screen.getByTestId("export-button")).toBeEnabled();
  });

  it("rejette une extension incorrecte", () => {
    render(<HomePage />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const txt = new File([new Uint8Array([1, 2, 3])], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [txt] } });
    expect(screen.getByTestId("error")).toHaveTextContent("Unsupported file type");
  });

  it("affiche FAIL et laisse l'export désactivé", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...passResponse,
          roundtrip: { ...passResponse.roundtrip, result: "FAIL", bit_identical: false },
          export_allowed: false,
          export_warning: "EXPORT DISABLED",
        }),
      }),
    );
    render(<HomePage />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    await user.upload(
      input,
      new File([new Uint8Array([80, 75, 3, 4])], "notes.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );
    await user.click(screen.getByRole("button", { name: /Générer et valider/ }));
    await waitFor(() => expect(screen.getByTestId("roundtrip")).toHaveTextContent("ROUND-TRIP : FAIL"));
    expect(screen.getByTestId("export-button")).toBeDisabled();
  });

  it("réinitialise les paramètres", async () => {
    const user = userEvent.setup();
    render(<HomePage />);
    await user.click(screen.getAllByRole("button", { name: "ON" })[0]);
    expect(screen.getAllByRole("button", { name: "OFF" })[0]).toHaveTextContent("OFF");
    await user.click(screen.getByRole("button", { name: "Réinitialiser les paramètres" }));
    expect(screen.getAllByRole("button", { name: "ON" })).toHaveLength(3);
  });

  it("permet d'afficher et de masquer les informations pédagogiques", async () => {
    const user = userEvent.setup();
    render(<HomePage />);
    expect(screen.queryByText("1. Compression — ON")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Afficher les explications ▼" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Afficher les explications ▼" }));
    expect(screen.getByText("1. Compression — ON")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Masquer les explications ▲" })).toHaveLength(2);

    await user.click(screen.getAllByRole("button", { name: "Masquer les explications ▲" })[0]);
    expect(screen.queryByText("1. Compression — ON")).not.toBeInTheDocument();
  });
});
