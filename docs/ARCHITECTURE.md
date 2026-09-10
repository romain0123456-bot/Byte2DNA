# Architecture Byte2DNA — BYTE2DNA-POC-1

## Objectif

Démontrer un round-trip **vérifiable** :

```text
fichier original
  → bytes
  → fragments ADN (A/C/G/T)
  → décodage
  → bytes
  → fichier reconstruit
```

avec `original_bytes == reconstructed_bytes` et SHA-256 identiques.

Le décodeur ne reçoit **jamais** les octets originaux. Il ne voit que :

- la liste des séquences ADN ;
- les métadonnées de format (`DecodeMetadata`, validées strictement : version, en-tête de variant, taille d'index et paramètres ECC).

## Composants

| Couche | Rôle |
| --- | --- |
| `frontend/` | Page unique Next.js : import, paramètres, résultats, export |
| `backend/app/main.py` | HTTP : `GET /health`, `POST /api/encode`, `POST /api/export` |
| `encoder.py` / `decoder.py` | Codec utilisable sans FastAPI |
| `fragmenter.py` | Découpage à capacité fixe |
| `constraints.py` | GC %, homopolymère max, statut VALID/WARNING/INVALID |
| `validator.py` | Round-trip + mélange des fragments |
| `exporter.py` | Classeur XLSX 4 onglets |

Pas de base de données. Les résultats d’encodage sont gardés en mémoire le temps de l’export.

## Encodage d’un fichier

1. Validation binaire du fichier (limite 5 Mo appliquée avant lecture complète ; validation conteneur DOCX vérifiant `[Content_Types].xml` et `word/document.xml` sans parsing XML ni extraction disque).
2. SHA-256 du fichier original (toujours, même si l’export SHA-256 est OFF).
3. Compression zlib optionnelle.
4. En-tête interne : `B2D1 | flags | original_size | data_size | payload`.
5. Découpage en chunks de `payload_capacity` octets (dernier chunk paddé avec des zéros).
6. Pour chaque chunk : index 32 bits + payload, ECC optionnelle, scrambling XOR, ADN.
7. Choix déterministe d’un **variant 0–255** jusqu’à respecter GC / homopolymères.
8. Validation round-trip : les séquences sont mélangées puis décodées.

## Structure d’un fragment

```text
[variant_header 8 nt][corps scrambé][filler jusqu’à 100/150/200 nt]
```

- **Variant header** : 8 nucléotides, 1 bit/nt, positions paires `C/G`, impaires `A/T`. GC = 50 %, homopolymère = 1. Encode le seed 0–255.
- **Corps** : `bytes_to_dna(XOR(index||payload[||ecc], SHA256-keystream(version, variant)))`.
- **Index** : entier big-endian 32 bits, lu après descrambling. Identifiant humain `DNA000001`.
- **Filler** : nucléotides restants (longueur cible − corps), ignorés au décodage.

Mapping après descrambling (longueur multiple de 4, alphabet strict `A/C/G/T` sans masquage) :

```text
00 → A
01 → C
10 → G
11 → T
```

## Contraintes

Pour chaque séquence complète :

```text
GC% = (G+C) / longueur × 100
```

- `VALID` : GC dans [min, max] et homopolymère ≤ max
- `WARNING` : jusqu’à 5 points de GC hors bornes et/ou 1 base d’homopolymère en trop
- `INVALID` : au-delà, ou aucune variante compatible parmi 256 essais (le fragment est tout de même émis, jamais masqué)

L’UI distingue le succès d’encodage (`ENCODING VALID`) du respect des contraintes de synthèse (`SYNTHESIS CONSTRAINTS PASS`).

## API

`POST /api/encode` (multipart) : fichier + paramètres → JSON (stats, aperçu, round-trip, `result_id`).

`POST /api/export` : `{ "result_id": "..." }` → XLSX si et seulement si `ROUND-TRIP == PASS`.

`GET /health` → `{"status":"ok"}`.

## Hors scope V1

Authentification, cloud, fournisseurs de synthèse, amorces, Fountain codes, base de données, LLM.
