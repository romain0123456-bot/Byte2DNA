"use client";

import { useMemo, useRef, useState } from "react";
import { decodeExcelFile, downloadRestoredFile, downloadXlsx, encodeFile } from "@/lib/api";
import { API_BASE, DEFAULT_PARAMS, type EncodeParams } from "@/lib/constants";
import { formatBytes, sha256File, validateClientFile } from "@/lib/fileValidation";
import type { DecodeResponse, EncodeResponse } from "@/lib/types";

export default function HomePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [sha256, setSha256] = useState<string>("");
  const [params, setParams] = useState<EncodeParams>({ ...DEFAULT_PARAMS });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<EncodeResponse | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [mode, setMode] = useState<"encode" | "decode">("encode");

  // State for decoding inverse
  const decodeInputRef = useRef<HTMLInputElement>(null);
  const [decodeDragOver, setDecodeDragOver] = useState(false);
  const [decodeFile, setDecodeFile] = useState<File | null>(null);
  const [decodeBusy, setDecodeBusy] = useState(false);
  const [decodeError, setDecodeError] = useState("");
  const [decodeResult, setDecodeResult] = useState<DecodeResponse | null>(null);

  const fileLabel = useMemo(() => {
    if (!file) return null;
    const extension = file.name.split(".").pop()?.toUpperCase() || "";
    return { name: file.name, extension, size: formatBytes(file.size) };
  }, [file]);

  const decodeFileLabel = useMemo(() => {
    if (!decodeFile) return null;
    const extension = decodeFile.name.split(".").pop()?.toUpperCase() || "";
    return { name: decodeFile.name, extension, size: formatBytes(decodeFile.size) };
  }, [decodeFile]);

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

  function onDecodeFileSelect(next: File | null) {
    setDecodeError("");
    setDecodeResult(null);
    if (!next) {
      setDecodeFile(null);
      return;
    }
    const name = next.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".xls")) {
      setDecodeFile(null);
      setDecodeError("Format non supporté : veuillez sélectionner un fichier Excel (.xlsx ou .xls)");
      return;
    }
    setDecodeFile(next);
  }

  async function onRunDecode() {
    if (!decodeFile) {
      setDecodeError("Veuillez importer un fichier Excel (.xlsx ou .xls)");
      return;
    }
    setDecodeBusy(true);
    setDecodeError("");
    try {
      const resp = await decodeExcelFile(decodeFile);
      setDecodeResult(resp);
    } catch (err) {
      setDecodeResult(null);
      setDecodeError(err instanceof Error ? err.message : "Décodage impossible");
    } finally {
      setDecodeBusy(false);
    }
  }

  async function onDownloadRestored() {
    if (!decodeResult) return;
    try {
      await downloadRestoredFile(decodeResult.decode_id, decodeResult.filename);
    } catch (err) {
      setDecodeError(err instanceof Error ? err.message : "Téléchargement impossible");
    }
  }

  async function onGenerate() {
    if (!file) {
      setError("Importer un document");
      return;
    }
    if (params.gcMin > params.gcMax) {
      setError("Le GC minimum ne peut pas être supérieur au GC maximum");
      return;
    }
    if (params.homopolymerMax < 1 || params.homopolymerMax > 10) {
      setError("L'homopolymère maximum doit être compris entre 1 et 10");
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
    const stem =
      result.file.original_filename
        .replace(/\.[^/.]+$/, "")
        .replace(/[^a-zA-Z0-9_-]/g, "_") || "export";
    const suggestedFilename = `byte2dna_${stem}.xlsx`;
    try {
      await downloadXlsx(result.result_id, suggestedFilename);
    } catch (err) {
      try {
        const directUrl = `${API_BASE}/api/export?result_id=${encodeURIComponent(result.result_id)}`;
        window.location.assign(directUrl);
      } catch {
        setError(err instanceof Error ? err.message : "Export failed");
      }
    } finally {
      setBusy(false);
    }
  }

  const exportEnabled = Boolean(result?.export_allowed) && !busy;
  const roundtripPass = result?.roundtrip.result === "PASS";

  return (
    <main className="page">
      <header className="hero">
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.jpeg"
            alt="Byte2DNA Logo"
            className="logo"
            width={136}
            height={136}
          />
          <div>
            <p className="kicker">Generic POC · BYTE2DNA-POC-1</p>
            <h1>Byte2DNA</h1>
            <p className="subtitle">Du fichier à la séquence ADN</p>
          </div>
        </div>
        <div className="badge">Stockage numérique expérimental</div>
      </header>

      <div className="tab-bar">
        <button
          type="button"
          className={`tab-btn ${mode === "encode" ? "active" : ""}`}
          onClick={() => setMode("encode")}
          data-testid="tab-encode"
        >
          🧬 Encodage (Document → ADN)
        </button>
        <button
          type="button"
          className={`tab-btn ${mode === "decode" ? "active" : ""}`}
          onClick={() => setMode("decode")}
          data-testid="tab-decode"
        >
          🔄 Restauration inverse (Excel ADN → Document)
        </button>
      </div>

      {mode === "encode" && (
        <>
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
            <p className="hint">Formats : PDF, DOCX, DOC · Taille max : 5 Mo</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword"
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
            hint="Réduit le nombre de nucléotides via zlib"
            onChange={(compression) => setParams((p) => ({ ...p, compression }))}
          />
          <Toggle
            label="SHA-256 export"
            value={params.includeSha256Export}
            disabled={busy}
            hint="Consigne les hashs originaux et reconstruits dans le XLSX"
            onChange={(includeSha256Export) => setParams((p) => ({ ...p, includeSha256Export }))}
          />
          <Toggle
            label="Correction d'erreurs"
            value={params.ecc}
            disabled={busy}
            hint="Reed-Solomon (nsym = 8) par fragment"
            onChange={(ecc) => setParams((p) => ({ ...p, ecc }))}
          />
          <div className="row">
            <div>
              <span>Longueur fragment</span>
              <p className="field-hint">Taille cible de chaque séquence</p>
            </div>
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
                aria-label="GC minimum"
                type="number"
                min={0}
                max={100}
                disabled={busy}
                value={params.gcMin}
                onChange={(event) => setParams((p) => ({ ...p, gcMin: Number(event.target.value) }))}
              />
              <span className="field-hint">Borne basse cible</span>
            </label>
            <label className="field">
              GC maximum
              <input
                aria-label="GC maximum"
                type="number"
                min={0}
                max={100}
                disabled={busy}
                value={params.gcMax}
                onChange={(event) => setParams((p) => ({ ...p, gcMax: Number(event.target.value) }))}
              />
              <span className="field-hint">Borne haute cible</span>
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
              <span className="field-hint">Répétitions consécutives de la même base</span>
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

      <section className="card guide-card">
        <div
          className="guide-header"
          role="button"
          tabIndex={0}
          onClick={() => setShowGuide((prev) => !prev)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setShowGuide((prev) => !prev);
            }
          }}
          aria-expanded={showGuide}
          aria-controls="guide-content"
          data-testid="toggle-guide-header"
        >
          <div className="guide-header-title">
            <span className="guide-icon">💡</span>
            <h2>Comprendre les paramètres de génération</h2>
            <span className="guide-tag">Informations pédagogiques</span>
          </div>
          <button
            type="button"
            className="guide-toggle-btn"
            onClick={(e) => {
              e.stopPropagation();
              setShowGuide((prev) => !prev);
            }}
          >
            {showGuide ? "Masquer les explications ▲" : "Afficher les explications ▼"}
          </button>
        </div>

        {showGuide && (
          <div className="guide-content" id="guide-content">
            <div className="guide-item">
              <h3>1. Compression — ON</h3>
              <p>Avant de transformer le fichier en ADN, Byte2DNA peut le compresser avec zlib.</p>
              <p>Par exemple :</p>
              <pre className="guide-diagram">
{`Fichier Word : 20 Ko
       ↓
    zlib
       ↓
Données : 12 Ko
       ↓
Encodage ADN`}
              </pre>
              <p>Moins d&apos;octets signifie moins de nucléotides à synthétiser.</p>
              <p>
                C&apos;est particulièrement intéressant parce que la synthèse physique d&apos;ADN est liée au nombre de bases produites.
              </p>
              <p>Le décodeur fait ensuite l&apos;inverse :</p>
              <div style={{ margin: "8px 0" }}>
                <span className="guide-mono">ADN → données compressées → zlib → fichier original</span>
              </div>
              <span className="guide-recommendation">Je laisserais donc ON pratiquement tout le temps.</span>
            </div>

            <div className="guide-item">
              <h3>2. SHA-256 export — ON</h3>
              <p>Le SHA-256 est l&apos;empreinte numérique de ton fichier.</p>
              <p>Ton fichier possède par exemple :</p>
              <pre className="guide-diagram">
{`SHA-256 original
a9f63e...42bc

Après le processus :
PDF
 ↓
ADN
 ↓
PDF reconstruit

Byte2DNA recalcule :
SHA-256 reconstruit
a9f63e...42bc`}
              </pre>
              <p>
                Si :
              </p>
              <pre className="guide-diagram">
{`SHA256 original
       =
SHA256 reconstruit`}
              </pre>
              <p>tu sais que le fichier reconstruit est strictement identique bit à bit.</p>
              <p>
                Le paramètre SHA-256 export ON signifie surtout que cette information est également enregistrée dans le XLSX.
              </p>
              <span className="guide-recommendation">Je laisserais toujours ON pour ton POC.</span>
            </div>

            <div className="guide-item">
              <h3>3. Correction d&apos;erreurs — ON</h3>
              <p>C&apos;est déjà plus spécifique au stockage ADN.</p>
              <p>
                Une molécule d&apos;ADN synthétisée puis séquencée peut subir des erreurs. Byte2DNA ajoute donc actuellement un petit code Reed-Solomon à chaque fragment.
              </p>
              <p>Conceptuellement :</p>
              <pre className="guide-diagram">
{`Données
ABCDEFGH

        ↓ Reed-Solomon

ABCDEFGH + informations de correction`}
              </pre>
              <p>
                Si certaines informations sont altérées, Reed-Solomon peut permettre de les retrouver.
              </p>
              <p>Dans ton POC, la configuration actuelle utilise :</p>
              <pre className="guide-diagram">
{`Reed-Solomon
nsym = 8`}
              </pre>
              <p>Cela augmente légèrement la quantité d&apos;ADN nécessaire mais apporte de la robustesse.</p>
              <span className="guide-recommendation">ON est donc le meilleur choix pour ta démonstration.</span>
              <p className="guide-warning">
                Attention toutefois : le POC simule cette protection numériquement. Il ne reproduit pas encore tout le comportement réel d&apos;un canal synthèse → stockage → séquençage.
              </p>
            </div>

            <div className="guide-item">
              <h3>4. Longueur fragment — 100 / 150 / 200 nt</h3>
              <p>C&apos;est la longueur d&apos;une séquence ADN produite.</p>
              <p><strong>nt</strong> signifie nucléotide.</p>
              <p>
                Par exemple : <code>ACGTCAGTACGT...</code> avec exactement 150 caractères donne : <strong>150 nt</strong>.
              </p>
              <p>Byte2DNA découpe donc ton fichier en de nombreuses séquences :</p>
              <pre className="guide-diagram">
{`DNA000001  150 nt
DNA000002  150 nt
DNA000003  150 nt
DNA000004  150 nt
...`}
              </pre>
              <p><strong>Pourquoi ne pas créer une seule séquence gigantesque ?</strong></p>
              <p>
                Parce que la synthèse et le séquençage réels travaillent généralement avec des oligonucléotides courts.
              </p>
              <p>Dans Byte2DNA, chaque fragment contient en plus du contenu utile :</p>
              <pre className="guide-diagram">
{`┌──────────────────────────────┐
│ informations d'encodage      │
├──────────────────────────────┤
│ index du fragment            │
├──────────────────────────────┤
│ données du fichier           │
├──────────────────────────────┤
│ Reed-Solomon                 │
└──────────────────────────────┘
             150 nt`}
              </pre>
              <p>L&apos;index est essentiel car les molécules ne vont pas nécessairement revenir dans l&apos;ordre :</p>
              <pre className="guide-diagram">
{`DNA003
DNA001
DNA004
DNA002

Byte2DNA utilise l'index pour reconstruire :
DNA001
DNA002
DNA003
DNA004`}
              </pre>
              <span className="guide-recommendation">Pour ton POC, je choisirais 150 nt. C&apos;est un bon compromis pédagogique.</span>
            </div>

            <div className="guide-item">
              <h3>5. GC minimum / maximum</h3>
              <p>L&apos;ADN contient quatre bases :</p>
              <p>
                <strong>A</strong> = Adénine · <strong>C</strong> = Cytosine · <strong>G</strong> = Guanine · <strong>T</strong> = Thymine
              </p>
              <p>Le taux GC correspond à la proportion de <strong>G + C</strong> dans la séquence.</p>
              <p>Prenons : <code>ACGTACGT</code></p>
              <pre className="guide-diagram">
{`Il y a :
A = 2
C = 2
G = 2
T = 2

Donc :
GC = (2 + 2) / 8
   = 50 %`}
              </pre>
              <p><strong>Pourquoi cela compte ?</strong></p>
              <p>Une séquence extrêmement déséquilibrée peut être plus problématique à synthétiser ou séquencer.</p>
              <p>Pour ton profil générique : <strong>GC minimum = 40 % · GC maximum = 60 %</strong>.</p>
              <p>Byte2DNA essaie donc de produire des fragments compris dans cette zone :</p>
              <pre className="guide-diagram">
{`39 % GC  → hors cible
47 % GC  → OK
52 % GC  → OK
63 % GC  → hors cible`}
              </pre>
              <span className="guide-recommendation">
                40–60 % est une bonne plage pour le POC, mais ce n&apos;est pas une règle universelle de tous les prestataires.
              </span>
            </div>

            <div className="guide-item">
              <h3>6. Homopolymère maximum — 3</h3>
              <p>Un homopolymère est une répétition consécutive de la même base.</p>
              <p>Par exemple :</p>
              <pre className="guide-diagram">
{`ACGTACGT   → max = 1
ACGTTTAC   → contient TTT   → homopolymère max = 3
ACGTTTTAC  → contient TTTT  → homopolymère max = 4`}
              </pre>
              <p>
                Avec ton réglage <strong>Homopolymère maximum = 3</strong>, Byte2DNA cherche donc à éviter <code>AAAA</code>, <code>CCCC</code>, <code>GGGG</code>, <code>TTTT</code> et les répétitions encore plus longues.
              </p>
              <p>
                C&apos;est utile car les longues répétitions d&apos;une même base peuvent compliquer certaines opérations de synthèse/séquençage.
              </p>
            </div>

            <div className="guide-item highlight">
              <h3>Ce que fait Byte2DNA avec GC et homopolymères</h3>
              <p>C&apos;est une partie intéressante de ton POC.</p>
              <p>Byte2DNA ne se contente pas de faire :</p>
              <pre className="guide-diagram">
{`00 → A
01 → C
10 → G
11 → T`}
              </pre>
              <p>
                Il peut essayer jusqu&apos;à <strong>256 variantes déterministes</strong> de l&apos;encodage d&apos;un fragment pour trouver une représentation qui respecte mieux :
              </p>
              <pre className="guide-diagram">
{`GC = 40–60 %
ET
homopolymère ≤ 3`}
              </pre>
              <p>
                Donc plusieurs représentations ADN possibles des mêmes données sont essayées, tout en restant parfaitement réversibles.
              </p>
              <p>
                Le numéro de variante est conservé dans le fragment afin que le décodeur sache exactement comment revenir aux données originales.
              </p>
            </div>

            <div className="guide-footer-actions">
              <button
                type="button"
                className="ghost"
                onClick={() => setShowGuide(false)}
              >
                Masquer les explications ▲
              </button>
            </div>
          </div>
        )}
      </section>

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

          <div className="export-actions">
            <button
              className="secondary"
              type="button"
              data-testid="export-button"
              disabled={!exportEnabled}
              onClick={() => void onExport()}
            >
              Télécharger XLSX
            </button>
            {result.export_allowed && (
              <a
                href={`${API_BASE}/api/export?result_id=${encodeURIComponent(result.result_id)}`}
                download={`byte2dna_${result.file.original_filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_-]/g, "_") || "export"}.xlsx`}
                target="_blank"
                rel="noopener noreferrer"
                className="direct-download-link"
              >
                Téléchargement direct (secours)
              </a>
            )}
          </div>

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
        </>
      )}

      {mode === "decode" && (
        <section className="decode-container">
          <div className="card">
            <h2>Importer un classeur ADN (.xlsx / .xls)</h2>
            <p className="hint">
              Sélectionnez un classeur Excel contenant une feuille <code>SEQUENCES</code> et <code>METADATA</code> pour restaurer le fichier d&apos;origine bit-à-bit.
            </p>
            <div
              className={`dropzone${decodeDragOver ? " active" : ""}`}
              onClick={() => decodeInputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDecodeDragOver(true);
              }}
              onDragLeave={() => setDecodeDragOver(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDecodeDragOver(false);
                void onDecodeFileSelect(event.dataTransfer.files[0] ?? null);
              }}
            >
              <strong>Glisser-déposer le classeur Excel</strong>
              <p className="hint">ou cliquer pour choisir un fichier</p>
              <p className="hint">Formats acceptés : .xlsx, .xls</p>
              <input
                ref={decodeInputRef}
                type="file"
                accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                data-testid="decode-file-input"
                onChange={(event) => void onDecodeFileSelect(event.target.files?.[0] ?? null)}
              />
            </div>
            {decodeFileLabel && (
              <div className="file-meta" data-testid="decode-file-meta">
                <strong>{decodeFileLabel.name}</strong>
                <div>Type : {decodeFileLabel.extension}</div>
                <div>Taille : {decodeFileLabel.size}</div>
              </div>
            )}
            <div style={{ marginTop: 20 }}>
              <button
                className="primary"
                type="button"
                disabled={decodeBusy || !decodeFile}
                onClick={() => void onRunDecode()}
                data-testid="run-decode-button"
              >
                Décoder et restaurer le document d&apos;origine
              </button>
              {decodeBusy && (
                <p className="progress">Reconstruction et vérification bit-à-bit en cours…</p>
              )}
              {decodeError && (
                <div className="error" data-testid="decode-error">
                  {decodeError}
                </div>
              )}
            </div>
          </div>

          {decodeResult && (
            <section className="card" data-testid="decode-results">
              <h2>Document restauré avec succès</h2>
              <div className="stats">
                <div className="stat">
                  <span>Fichier restauré</span>
                  <strong style={{ fontSize: 16 }}>{decodeResult.filename}</strong>
                </div>
                <div className="stat">
                  <span>Taille</span>
                  <strong>{formatBytes(decodeResult.size)}</strong>
                </div>
                <div className="stat">
                  <span>Fragments traités</span>
                  <strong>{decodeResult.fragment_count.toLocaleString("fr-FR")}</strong>
                </div>
                <div className="stat">
                  <span>Compression</span>
                  <strong>{decodeResult.compression ? "ON (zlib)" : "OFF"}</strong>
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <p>
                  <strong>SHA-256 reconstruit :</strong>{" "}
                  <span className="hash" style={{ wordBreak: "break-all" }}>{decodeResult.sha256}</span>
                </p>
                {decodeResult.sha256_matched === true && (
                  <div className="recon-badge pass">
                    ✓ Fichier reconstruit bit-à-bit (SHA-256 conforme au document original)
                  </div>
                )}
                {decodeResult.sha256_matched === false && (
                  <div className="recon-badge warn">
                    ⚠ Empreinte différente du hash original enregistré dans l&apos;Excel
                  </div>
                )}
                {decodeResult.sha256_matched === null && (
                  <div className="recon-badge pass">
                    ✓ Document restauré avec succès (empreinte originale non consignée)
                  </div>
                )}
              </div>

              <div className="export-actions" style={{ marginTop: 24 }}>
                <button
                  type="button"
                  className="primary"
                  onClick={() => void onDownloadRestored()}
                  data-testid="download-restored-button"
                >
                  Télécharger le fichier restauré ({decodeResult.filename})
                </button>
              </div>
            </section>
          )}
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
  hint,
}: {
  label: string;
  value: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
  hint?: string;
}) {
  return (
    <div className="row">
      <div>
        <span>{label}</span>
        {hint && <p className="field-hint">{hint}</p>}
      </div>
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
