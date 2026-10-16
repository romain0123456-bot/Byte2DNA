# API HTTP — Byte2DNA (BYTE2DNA-POC-1)

Référence des routes FastAPI **existantes**, lue dans `backend/app/main.py`. Aucune route n'est ajoutée ni modifiée. Les références `fichier:ligne` renvoient au code à la date du document.

Application : `FastAPI(title="Byte2DNA", version="BYTE2DNA-POC-1")` (`main.py:38`, `constants.py:3-4`). Pas d'authentification. CORS : origines `localhost` / `127.0.0.1` (tout port) uniquement, en-tête `Content-Disposition` exposé (`main.py:37-54`).

## Routes

| Méthode | Chemin | Rôle |
| --- | --- | --- |
| GET | `/health` | Sonde de vie (`main.py:110`) |
| POST | `/api/encode` | Fichier → fragments ADN + round-trip (`main.py:115`) |
| GET, HEAD | `/api/export?result_id=…` | Télécharge le XLSX (`main.py:249`) |
| POST | `/api/export` | Idem, `result_id` en JSON (`main.py:254`) |
| POST | `/api/decode` | XLSX → fichier reconstruit (`main.py:259`) |
| GET | `/api/decode/download?decode_id=…` | Télécharge le fichier reconstruit (`main.py:315`) |

### GET /health

Réponse `200` : `{"status": "ok"}` (`main.py:110-112`).

### POST /api/encode

`multipart/form-data` (`main.py:115-126`) :

| Champ | Type | Défaut | Contrainte |
| --- | --- | --- | --- |
| `file` | fichier | requis | `.pdf`, `.docx`, `.doc`, 1 octet à 5 Mo |
| `compression` | texte | `"true"` | vrai si `1`, `true`, `on`, `yes` (insensible à la casse), sinon faux (`main.py:99-102`) |
| `include_sha256_export` | texte | `"true"` | idem |
| `ecc` | texte | `"true"` | idem |
| `fragment_length` | entier | `150` | `100`, `150` ou `200` (`models.py:36-44`) |
| `gc_min` | flottant | `40` | 0–100 |
| `gc_max` | flottant | `60` | 0–100 et ≥ `gc_min` (`models.py:52-61`) |
| `homopolymer_max` | entier | `3` | 1–10 (`models.py:45-50`) |

Réponse `200` (`ApiEncodeResponse`, `models.py:132-145`) :

| Champ | Type |
| --- | --- |
| `encoding_version` | texte (`BYTE2DNA-POC-1`) |
| `result_id` | texte (UUID hex, 32 caractères) |
| `file` | `original_filename`, `original_extension`, `original_size`, `sha256_original` |
| `stats` | `fragment_count`, `total_nucleotides`, `gc_average`, `gc_min_observed`, `gc_max_observed`, `max_homopolymer_observed`, `original_size`, `compressed_size`, `compression_ratio`, `compression`, `fragments_valid`, `fragments_warning`, `fragments_invalid`, `payload_capacity` |
| `roundtrip` | `result` (`PASS`/`FAIL`), `sha256_original`, `sha256_reconstructed` (nullable), `reconstructed_size` (nullable), `message`, `bit_identical` |
| `fragments_preview` | 40 premiers fragments (`main.py:174`) : `fragment_id`, `index`, `sequence`, `length_nt`, `gc_percent`, `max_homopolymer`, `encoding_variant`, `ecc`, `status` (`VALID`/`WARNING`/`INVALID`) |
| `fragment_count` | entier |
| `synthesis_review_required` | booléen : au moins un fragment `WARNING` ou `INVALID` (`main.py:158`) |
| `export_allowed` | booléen : `roundtrip.result == "PASS"` (`main.py:159`) |
| `export_warning` | `null`, `"Séquences nécessitant une revue avant synthèse"` (export permis + revue requise) ou `"EXPORT DISABLED"` (round-trip en échec) (`main.py:160-164`) |
| `qc_message` | `ENCODING VALID` ou `ENCODING COMPLETE — SOME FRAGMENTS INVALID`, suivi de ` / SYNTHESIS CONSTRAINTS PASS` ou ` / SYNTHESIS CONSTRAINTS NEED REVIEW` (`main.py:179-190`) |
| `profile` | `"Generic POC"` |

Quand le round-trip est `PASS`, un XLSX est écrit en arrière-plan dans `<tmp>/byte2dna_exports/` (`main.py:165-166`). Le résultat est gardé en mémoire (128 entrées max, `constants.py:35`) ; pas de base de données.

### GET, HEAD /api/export et POST /api/export

- `GET`/`HEAD` : paramètre de requête `result_id` (requis, texte).
- `POST` : corps JSON `{"result_id": "<id>"}`, `result_id` d'au moins 8 caractères (`models.py:147-148`).

Réponse `200` : XLSX (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), en-tête `Content-Disposition: attachment; filename="…"`, `Cache-Control: no-cache, no-store, must-revalidate`. `HEAD` renvoie les mêmes en-têtes avec un corps vide (`main.py:234-248`). L'export est servi depuis le disque s'il existe, sinon reconstruit depuis le cache mémoire (`main.py:196-229`). Classeur : onglets `SEQUENCES`, `METADATA`, `QC`, `DECODING` (`tests/test_api.py:77-86`).

### POST /api/decode

`multipart/form-data` : un champ `file` (requis), `.xlsx` ou `.xls`, 50 Mo max (`main.py:259-275`).

Réponse `200` (`ApiDecodeResponse`, `models.py:156-166`) : `decode_id`, `filename`, `size`, `sha256`, `sha256_original` (nullable), `sha256_matched` (nullable), `fragment_count`, `compression`, `ecc`, `download_url` (`/api/decode/download?decode_id=<decode_id>`, `main.py:311`).

### GET /api/decode/download

Paramètre de requête `decode_id` (requis). Réponse `200` : octets du fichier reconstruit, `Content-Disposition: attachment`, type `application/msword` (`.doc`), `…wordprocessingml.document` (`.docx`), `application/pdf` (`.pdf`), sinon `application/octet-stream` (`main.py:328-333`).

## Erreurs

Trois formes de corps existent. Elles ne sont pas unifiées dans le code.

| Forme | Origine | Exemple |
| --- | --- | --- |
| `{"error": "...", "detail": "..."}` | `UploadError` → handler `main.py:105-107`, toujours `400` | `{"error":"File too large","detail":"File too large"}` |
| `{"detail": "<texte>"}` | `HTTPException` | `{"detail":"Export failed"}` |
| `{"detail": [ {type, loc, msg, input, …} ]}` | validation FastAPI/pydantic, `422` | champ `file` manquant |

### Erreurs courantes d'utilisation

| Situation | Route | Statut | Corps | Source |
| --- | --- | --- | --- | --- |
| Extension hors `.pdf/.docx/.doc` | encode | 400 | `{"error":"Unsupported file type","detail":"Unsupported file type"}` | `files.py:38-39` ; test `test_api.py:53` |
| PDF ne commençant pas par `%PDF` | encode | 400 | idem | `files.py:43-44` ; `test_files.py:39` |
| DOCX non conforme (pas `PK`, ZIP invalide, ou `[Content_Types].xml` / `word/document.xml` absent) | encode | 400 | idem | `files.py:47-63` ; `test_files.py:51,65` |
| DOC sans signature OLE attendue | encode | 400 | idem | `files.py:65-67` ; `test_files.py:76` |
| `Content-Type` incompatible avec l'extension | encode | 400 | idem | `files.py:45,50-56,68-79` ; `test_files.py:81` |
| Fichier vide | encode | 400 | `{"error":"Empty file","detail":"Empty file"}` | `files.py:31-32` ; `test_api.py:54` |
| Fichier > 5 Mo (5 × 1024 × 1024 octets) | encode | 400 | `{"error":"File too large","detail":"File too large"}` | `main.py:127-129`, `constants.py:7` ; `test_api.py:59-65` |
| `fragment_length`, `homopolymer_max` ou bornes GC invalides | encode | 400 | `{"detail":"fragment_length must be one of (100, 150, 200)"}` (idem pour les autres messages de `models.py`) | `main.py:143-146` ; `test_api.py::test_invalid_encode_config_returns_400_detail_only` |
| Champ `file` absent | encode | 422 | corps de validation FastAPI, `loc: ["body","file"]` | `test_api.py::test_encode_without_file_returns_422` |
| Échec du codec (`ValueError`) | encode | 400 | `{"detail":"<message>"}` ou `"Encoding failed"` | `main.py:149-153` |
| **Échec du round-trip** | encode | **200** (pas d'erreur HTTP) | `roundtrip.result == "FAIL"`, `export_allowed: false`, `export_warning: "EXPORT DISABLED"` | `main.py:159-164`, `validator.py:26-55` ; `test_api.py::test_roundtrip_fail_disables_export` |
| Export d'un résultat en échec round-trip | export | 400 | `{"detail":"Export disabled: round-trip failed"}` | `main.py:211-213` ; même test |
| `result_id` inconnu ou expiré (hors cache mémoire et disque) | export | 404 | `{"detail":"Export failed"}` | `main.py:95` ; `test_api.py:87-88` |
| `result_id` < 8 caractères (POST) | export | 422 | validation pydantic | `models.py:147-148` |
| Champ de formulaire non numérique (`fragment_length`, `homopolymer_max`, `gc_min`, `gc_max`) | encode | 422 | corps de validation FastAPI (ex. `int_parsing`) | observé par sondage Sprint 3 |
| `result_id` absent (GET) ou `file` / `decode_id` absent | export, decode, download | 422 | corps de validation FastAPI | observé par sondage Sprint 3 |
| `result_id` / `decode_id` qui n'est pas 32 caractères hexadécimaux minuscules (ex. `../x`) | export, download | 404 | mêmes corps que pour un identifiant inconnu | `main.py` `_ID_RE` ; `test_api.py::test_path_traversal_ids_are_rejected` |
| Génération XLSX en erreur | export | 500 | `{"detail":"Export failed"}` | `main.py:214-217` (non testé) |
| Fichier vide | decode | 400 | `{"detail":"Fichier vide"}` | `main.py:266-267` |
| Extension hors `.xlsx/.xls` | decode | 400 | `{"detail":"Format non supporté : veuillez importer un classeur .xlsx ou .xls contenant des séquences ADN"}` | `main.py:269-275` ; `test_api.py::test_api_decode_invalid_files` |
| Fichier > 50 Mo | decode | 400 | `{"detail":"Fichier Excel trop volumineux (max 50 Mo)"}` | `main.py:264-265` |
| XLSX illisible (`.xls` illisible : `{"detail":"Invalid XLS file"}`) | decode | 400 | `{"detail":"Invalid XLSX file"}` | `excel_reader.py:49`, `main.py:277-280` ; `test_api.py::test_api_decode_invalid_files` |
| Reconstruction impossible | decode | 400 | `{"detail":"Decoding failed: could not reconstruct file from DNA sequences"}` | `reconstructor.py:35-37` |
| `decode_id` inconnu ou expiré | download | 404 | `{"detail":"Fichier restauré introuvable ou expiré"}` | `main.py:320-321` ; `test_api.py::test_api_decode_invalid_files` |

Remarques :

- Un round-trip en échec n'est **pas** une erreur HTTP à l'encodage : il faut lire `roundtrip.result` et `export_allowed` dans la réponse `200`.
- Les messages des erreurs d'upload sont en anglais ; ceux de `/api/decode` sont en français.
- Les messages renvoyés sont des textes fixes ou des messages de validation du codec. Aucun chemin de fichier ni trace d'appel n'est renvoyé dans les cas testés. Le nom de fichier est nettoyé (`sanitize_filename`, `files.py:24-27`).
