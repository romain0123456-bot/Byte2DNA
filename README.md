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

## Démarrage rapide

### Prérequis

- Python **3.12** (3.14 échoue à compiler `pydantic-core` avec les versions épinglées) ;
- Node.js 22 et npm (versions utilisées pour la vérification) ;
- ports libres : **8001** (backend FastAPI) et **3000** (frontend Next.js).

### Ports

| Service | Port | Remarque |
|---|---|---|
| Backend FastAPI | 8001 | port attendu par le proxy du frontend (`frontend/next.config.ts`) et par `frontend/src/lib/api.ts` |
| Frontend Next.js | 3000 | `npm run dev` |

Le navigateur appelle `/backend/*` ; Next.js proxyfie vers `API_PROXY_TARGET` (défaut `http://127.0.0.1:8001`).

### 1. Backend (terminal 1)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Vérifier : `curl http://127.0.0.1:8001/health` → `{"status":"ok"}`.

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Ouvrir [http://127.0.0.1:3000](http://127.0.0.1:3000).

Pour utiliser un autre port backend (ex. 8010) : lancer `uvicorn ... --port 8010` et `API_PROXY_TARGET=http://127.0.0.1:8010 npm run dev`. Limite connue : `/api/decode` et `/api/decode/download` (téléchargement du fichier restauré) gardent un repli direct codé en dur sur `127.0.0.1:8001` dans `frontend/src/lib/api.ts` (lignes 96, 104, 129) ; `API_PROXY_TARGET` ne les couvre pas.

### Diagnostic : backend indisponible

1. `curl http://127.0.0.1:8001/health` doit renvoyer `{"status":"ok"}` (HTTP 200). Sinon, le backend n’est pas lancé ou a échoué : relire la sortie d’`uvicorn`.
2. Réponse différente de `{"status":"ok"}` : **un autre service occupe peut-être le port 8001**. Vérifier avec `lsof -nP -iTCP:8001 -sTCP:LISTEN` (macOS/Linux) ou `netstat -ano | findstr :8001` (Windows), l’arrêter, ou utiliser un autre port (voir ci-dessus).
3. `pip install` échoue sur `pydantic-core` : vous n’êtes pas en Python 3.12.
4. Health OK mais l’UI affiche une erreur : vérifier que `API_PROXY_TARGET` pointe vers le bon port, puis redémarrer `npm run dev`.

## Utilisation

1. ouvrir l’application ;
2. importer un PDF ou un DOCX (max 5 Mo) ;
3. configurer compression, ECC, longueur de fragment, GC, homopolymères ;
4. cliquer sur **Générer et valider les séquences ADN** ;
5. vérifier **ROUND-TRIP : PASS** ;
6. télécharger le XLSX (onglets `SEQUENCES`, `METADATA`, `QC`, `DECODING`).

L’export est **interdit** si le round-trip échoue. S’il passe mais que des fragments sont en WARNING/INVALID, l’export reste possible avec l’avertissement *Séquences nécessitant une revue avant synthèse*.

## Tests

Backend (depuis le venv activé) :

```bash
cd backend
python -m pytest
```

Résultat constaté (Python 3.12, 2026-10-15) : `111 passed`.

Frontend :

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

Résultat constaté (Node 22) : `npm test` 15 tests passés, `typecheck` et `build` sans erreur.

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
