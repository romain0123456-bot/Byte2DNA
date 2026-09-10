"use client";

import { useMemo, useRef, useState } from "react";
import { downloadXlsx, encodeFile } from "@/lib/api";
import { DEFAULT_PARAMS, type EncodeParams } from "@/lib/constants";
import { formatBytes, sha256File, validateClientFile } from "@/lib/fileValidation";
import type { EncodeResponse } from "@/lib/types";

export default function HomePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [sha256, setSha256] = useState<string>("");
  const [params, setParams] = useState<EncodeParams>({ ...DEFAULT_PARAMS });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<EncodeResponse | null>(null);

  const fileLabel = useMemo(() => {
    if (!file) return null;
    const extension = file.name.split(".").pop()?.toUpperCase() || "";
    return { name: file.name, extension, size: formatBytes(file.size) };
  }, [file]);

  async function onFile(next: File | null) {
    setError("");
    setResult(null);
    const check = validateClientFile(next);
    if (!check.ok) {
      setFile(null);
      setSha256("");
      setError(check.error);
      return;
    }
    setFile(next);
    try {
      setSha256(await sha256File(next as File));
    } catch {
      setSha256("");
    }
  }

  async function onGenerate() {
    if (!file) {
      setError("Importer un document");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const encoded = await encodeFile(file, params);
      setResult(encoded);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Encoding failed");
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    if (!result?.export_allowed) return;
    setBusy(true);
    setError("");
    try {
      await downloadXlsx(result.result_id, "byte2dna_export.xlsx");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  const exportEnabled = Boolean(result?.export_allowed) && !busy;
  const roundtripPass = result?.roundtrip.result === "PASS";

  return (
    <main className="page">
      <header className="hero">
        <div>
          <p className="kicker">Generic POC · BYTE2DNA-POC-1</p>
          <h1>Byte2DNA</h1>
          <p className="subtitle">Du fichier à la séquence ADN</p>
        </div>
        <div className="badge">Stockage numérique expérimental</div>
      </header>

      <section className="grid">
        <div className="card">
          <h2>Importer un document</h2>
          <div
            className={`dropzone${dragOver ? " active" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              void onFile(event.dataTransfer.files[0] ?? null);
            }}
          >
            <strong>Glisser-déposer un fichier</strong>
            <p className="hint">ou cliquer pour choisir un fichier</p>
            <p className="hint">Formats : PDF, DOCX · Taille max : 5 Mo</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              data-testid="file-input"
              onChange={(event) => void onFile(event.target.files?.[0] ?? null)}
            />
          </div>
          {fileLabel && (
            <div className="file-meta" data-testid="file-meta">
              <strong>{fileLabel.name}</strong>
              <div>Type : {fileLabel.extension}</div>
              <div>Taille : {fileLabel.size}</div>
              <div className="hash">SHA-256 : {sha256 || "calcul…"}</div>
            </div>
          )}
        </div>

        <div className="card">
          <h2>Paramètres d&apos;encodage</h2>
          <Toggle
            label="Compression"
            value={params.compression}
            disabled={busy}
            onChange={(compression) => setParams((p) => ({ ...p, compression }))}
          />
          <Toggle
            label="SHA-256 export"
            value={params.includeSha256Export}
            disabled={busy}
            onChange={(includeSha256Export) => setParams((p) => ({ ...p, includeSha256Export }))}
          />
          <Toggle
            label="Correction d'erreurs"
            value={params.ecc}
            disabled={busy}
            onChange={(ecc) => setParams((p) => ({ ...p, ecc }))}
          />
          <div className="row">
            <span>Longueur fragment</span>
            <select
              aria-label="Longueur fragment"
              disabled={busy}
              value={params.fragmentLength}
              onChange={(event) =>
                setParams((p) => ({ ...p, fragmentLength: Number(event.target.value) }))
              }
            >
              <option value={100}>100 nt</option>
              <option value={150}>150 nt</option>
              <option value={200}>200 nt</option>
            </select>
          </div>
          <div className="row">
            <label className="field">
              GC minimum
              <input
                type="number"
                min={0}
                max={100}
                disabled={busy}
                value={params.gcMin}
                onChange={(event) => setParams((p) => ({ ...p, gcMin: Number(event.target.value) }))}
              />
            </label>
            <label className="field">
              GC maximum
              <input
                type="number"
                min={0}
                max={100}
                disabled={busy}
                value={params.gcMax}
                onChange={(event) => setParams((p) => ({ ...p, gcMax: Number(event.target.value) }))}
              />
            </label>
          </div>
          <div className="row">
            <label className="field" style={{ width: "100%" }}>
              Homopolymère maximum
              <input
                type="number"
                min={1}
                max={10}
                disabled={busy}
                value={params.homopolymerMax}
                onChange={(event) =>
                  setParams((p) => ({ ...p, homopolymerMax: Number(event.target.value) }))
                }
              />
            </label>
          </div>
          <div className="actions">
            <button className="ghost" type="button" disabled={busy} onClick={() => setParams({ ...DEFAULT_PARAMS })}>
              Réinitialiser les paramètres
            </button>
          </div>
        </div>
      </section>

      <div className="generate-wrap">
        <button
          className="primary"
          type="button"
          disabled={busy || !file}
          onClick={() => void onGenerate()}
        >
          Générer et valider les séquences ADN
        </button>
        {busy && <p className="progress">Encodage et validation du round-trip en cours…</p>}
        {error && (
          <div className="error" data-testid="error">
            {error}
          </div>
        )}
      </div>

      {result && (
        <section className="card" data-testid="results">
          <h2>Encodage terminé</h2>
          <p className="hint">{result.qc_message}</p>
          <div className="stats">
            <div className="stat">
              <span>Fragments</span>
              <strong>{result.stats.fragment_count}</strong>
            </div>
            <div className="stat">
              <span>Nucléotides</span>
              <strong>{result.stats.total_nucleotides.toLocaleString("fr-FR")}</strong>
            </div>
            <div className="stat">
              <span>GC moyen</span>
              <strong>{result.stats.gc_average.toFixed(1)} %</strong>
            </div>
            <div className="stat">
              <span>Homopolymère max</span>
              <strong>{result.stats.max_homopolymer_observed}</strong>
            </div>
          </div>
          <p>
            GC min {result.stats.gc_min_observed.toFixed(1)} % · GC max{" "}
            {result.stats.gc_max_observed.toFixed(1)} %
          </p>
          <p>
            Compression {formatBytes(result.stats.original_size)} →{" "}
            {formatBytes(result.stats.compressed_size)}
            {result.stats.compression ? "" : " (désactivée)"}
          </p>

          <div className={`roundtrip ${roundtripPass ? "pass" : "fail"}`} data-testid="roundtrip">
            <h3>ROUND-TRIP VALIDATION</h3>
            <p>
              <strong>ROUND-TRIP : {result.roundtrip.result}</strong>
            </p>
            {roundtripPass ? (
              <>
                <p>✓ Fichier reconstruit bit-à-bit</p>
                <p>✓ SHA-256 identique</p>
              </>
            ) : (
              <>
                <p>Reconstruction incorrecte.</p>
                <p>EXPORT DISABLED</p>
              </>
            )}
          </div>

          {result.export_warning && (
            <div className="warning-banner">{result.export_warning}</div>
          )}

          <button
            className="secondary"
            type="button"
            data-testid="export-button"
            disabled={!exportEnabled}
            onClick={() => void onExport()}
          >
            Télécharger XLSX
          </button>

          <h2 style={{ marginTop: 24 }}>Aperçu des fragments</h2>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Longueur</th>
                <th>GC</th>
                <th>Homopolymère max</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {result.fragments_preview.map((fragment) => (
                <tr key={fragment.fragment_id}>
                  <td>{fragment.fragment_id}</td>
                  <td className="num">{fragment.length_nt}</td>
                  <td className="num">{fragment.gc_percent.toFixed(1)} %</td>
                  <td className="num">{fragment.max_homopolymer}</td>
                  <td>
                    <span className={`pill ${fragment.status}`}>{fragment.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <p className="disclaimer">
        Byte2DNA est un prototype expérimental. Les séquences générées doivent être validées selon
        les contraintes du prestataire de synthèse avant toute synthèse physique.
      </p>
    </main>
  );
}

function Toggle({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="row">
      <span>{label}</span>
      <button
        type="button"
        className={`toggle${value ? " on" : ""}`}
        disabled={disabled}
        aria-pressed={value}
        onClick={() => onChange(!value)}
      >
        {value ? "ON" : "OFF"}
      </button>
    </div>
  );
}
