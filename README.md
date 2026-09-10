# Byte2DNA

POC pédagogique de **stockage numérique sur ADN**.

Byte2DNA lit un petit fichier PDF ou DOCX comme un tableau d’octets, le convertit en séquences `A/C/G/T`, vérifie qu’on peut reconstruire **exactement** le fichier d’origine (octets identiques et SHA-256 identique), puis exporte les fragments dans un classeur Excel.

```text
File → Bytes → DNA → Bytes → File
```

Ce n’est **pas** un système industriel de DNA Data Storage. Aucune synthèse physique n’est déclenchée.

## Architecture

```text
Browser
  └── React / Next.js (frontend/)
        └── FastAPI (backend/)
              ├── file reader (binaire)
              ├── SHA-256
              ├── compression zlib
              ├── DNA encoder / decoder
              ├── fragmenter + indexer
              ├── contraintes GC / homopolymères
              ├── Reed-Solomon (reedsolo)
              ├── round-trip validator
              └── export XLSX (openpyxl)
```

Le codec Python est indépendant du serveur :

```python
from app.services.codec import encode, decode
```

## Installation backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Santé : [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → `{"status":"ok"}`

## Installation frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrir [http://127.0.0.1:3000](http://127.0.0.1:3000). Le frontend proxyfie `/backend/*` vers FastAPI (`API_PROXY_TARGET`, défaut `http://127.0.0.1:8000`).

## Utilisation

1. ouvrir l’application ;
2. importer un PDF ou un DOCX (max 5 Mo) ;
3. configurer compression, ECC, longueur de fragment, GC, homopolymères ;
4. cliquer sur **Générer et valider les séquences ADN** ;
5. vérifier **ROUND-TRIP : PASS** ;
6. télécharger le XLSX (onglets `SEQUENCES`, `METADATA`, `QC`, `DECODING`).

L’export est **interdit** si le round-trip échoue. S’il passe mais que des fragments sont en WARNING/INVALID, l’export reste possible avec l’avertissement *Séquences nécessitant une revue avant synthèse*.

## Tests

Backend :

```bash
cd backend
python -m pytest
```

Frontend :

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

## Format BYTE2DNA-POC-1

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

- mapping 2 bits : `00→A`, `01→C`, `10→G`, `11→T` après scrambling XOR déterministe (alphabet strict `A/C/G/T`, longueur multiple de 4) ;
- chaque fragment : en-tête de variant (8 nt) + corps scrambé contenant l’index et le payload ;
- validation stricte des métadonnées de décodage (`DecodeMetadata`) et rejet de toute incohérence ;
- validation DOCX durcie par vérification de la présence des entrées conteneur ZIP (`[Content_Types].xml` et `word/document.xml`) ;
- limite de 5 Mo appliquée avant lecture complète en mémoire ;
- compression optionnelle : `zlib` ;
- correction d’erreurs optionnelle : Reed-Solomon `reedsolo` (`nsym=8`) par fragment ;
- profil unique : **Generic POC** (aucun fournisseur de synthèse).

## Limites

- POC expérimental, pas une garantie de synthétisabilité.
- Aucune synthèse physique, aucun prestataire (Twist, IDT, Eurofins, …).
- Contraintes biologiques simplifiées (GC, homopolymères, longueur d’oligo).
- Pas de validation fournisseur, pas d’amorces biologiques, pas de stockage long terme.
- ECC simplifiée (Reed-Solomon court par fragment) ; elle n’est pas un canal de communication réel.
- Pas de redondance type Fountain / raptor : hors scope V1.
- Taille max 5 Mo ; l’interface n’accepte que PDF/DOCX, le moteur interne est générique `bytes ↔ DNA`.
