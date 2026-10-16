# Qualification Byte2DNA (Sprint 5)

Tous les résultats ci-dessous ont été **observés** en exécutant les commandes indiquées (2026-10-16). Rien n'est déduit ou supposé. Ce qui n'a pas été testé est listé en fin de document.

## 1. Environnement

| Élément | Local | CI (GitHub Actions, ubuntu-latest) |
| --- | --- | --- |
| Python | 3.12.13 (venv hors dépôt) | 3.12.15 (`actions/setup-python`, `python-version: '3.12'`) |
| Node | v22.23.1 | 22.x (`actions/setup-node`, `node-version: '22'`) |
| Dépendances backend | `backend/requirements.txt` (versions épinglées) | idem |
| Dépendances frontend | `npm ci` (`package-lock.json`) | idem |

## 2. Commandes et résultats

Depuis la racine du dépôt (venv Python 3.12 activé) :

| # | Commande | Résultat observé |
| --- | --- | --- |
| 1 | `cd backend && python -m pytest` | `130 passed, 1 warning` (avertissement de dépréciation starlette/anyio, préexistant) |
| 2 | `cd frontend && npm ci && npm test` | 2 fichiers, `17 passed` |
| 3 | `cd frontend && npm run typecheck` | sans erreur |
| 4 | `cd frontend && npm run build` | `Compiled successfully` |
| 5 | `PYTHONPATH=backend:backend/tests python qualification/sprint5/e2e_probe.py` | `ALL_OK` (voir 3) |

Le compte backend était de 129 avant Sprint 5 ; Sprint 5 ajoute 1 test (`test_path_traversal_ids_are_rejected`).

### Concordance CI / local (HEAD de la première poussée, `937388b`)

| Job | Résultat CI | Local | Lien |
| --- | --- | --- | --- |
| `backend-pytest` (push) | `130 passed, 1 warning` | `130 passed, 1 warning` | https://github.com/romain0123456-bot/Byte2DNA/actions/runs/38856438425/job/116828841375 |
| `frontend` (push) | `17 passed` (2 fichiers), typecheck et build OK | idem | https://github.com/romain0123456-bot/Byte2DNA/actions/runs/38856438425/job/116828841645 |
| `backend-pytest` (pull_request) | idem | idem | https://github.com/romain0123456-bot/Byte2DNA/actions/runs/38856445814/job/116828866255 |
| `frontend` (pull_request) | idem | idem | https://github.com/romain0123456-bot/Byte2DNA/actions/runs/38856445814/job/116828866089 |

Les comptes CI et locaux sont identiques. Le job `lot5-qualification` existant est conservé, inchangé. Il ne lance que `qualification/lot5/tests`. Le workflow ajouté est `.github/workflows/ci.yml`.

## 3. Cas de bout en bout (API, fixtures synthétiques légères)

Script : `qualification/sprint5/e2e_probe.py`. Il utilise les fixtures de `backend/tests/conftest.py` (PDF, DOCX et DOC minuscules, **synthétiques**, générés en mémoire, aucun document réel). Il enchaîne `POST /api/encode`, `GET /api/export`, ouverture du XLSX, `POST /api/decode`, `GET /api/decode/download`.

| Fichier | Taille (octets) | SHA-256 de l'original | Round-trip | Onglets XLSX | Octets restitués identiques | SHA-256 restitué identique |
| --- | --- | --- | --- | --- | --- | --- |
| fixture.pdf | 275 | `ee7a65ca5d3b5005d321e4ca0b216bb601c18084c6a6411819a95ba60897a6bc` | PASS | SEQUENCES, METADATA, QC, DECODING | oui | oui |
| fixture.docx | 372 | `fc130010a8c14fb8979940b017ec6496fbd72ce380d3f682a7d3f064eb402c4f` | PASS | idem | oui | oui |
| fixture.doc | 532 | `abc59be3f29d1598002fed82f82a13c5b53c46c784a24992ceb14c3076cff97b` | PASS | idem | oui | oui |

`sha256_matched` vaut `True` au décodage pour les trois cas. Fragments : 9 (PDF), 11 (DOCX), 3 (DOC), tous `valid`, 0 `warning`, 0 `invalid`.

## 4. Pull requests #1 à #7

Source : `gh pr list --state all` le 2026-10-16.

| PR | Titre | État | SHA de merge |
| --- | --- | --- | --- |
| #1 | feat: implement Byte2DNA end-to-end POC | MERGED | `c1ea9868d1264fb0dbec484f28903a917e98b0b1` |
| #2 | LOT5 A: label normalization and controlled red CI qualification | MERGED | `9862cc8ef4f5aa701e7af041d45608ab8c5525cf` |
| #3 | LOT5 B: timeouts (controlled P1 initial) | MERGED | `0ffdc32394a84cb3d2e1249c42d1f3e4995b6e01` |
| #4 | Sprint 1: README quick start | MERGED | `d7dd44fb93f5000a89c64532b15ea1991208a504` |
| #5 | test(codec): strengthen byte-preservation round-trip tests | MERGED | `11d93d0a17e5941c47ddb7305196f3d428c92a3c` |
| #6 | docs(api): document routes and error responses; negative tests | MERGED | `79f7b30bfb275835b8cf6f3110f516019df34c09` |
| #7 | feat(frontend): clarify POC result states (Sprint 4) | MERGED | `e745638ed50a2ec4650b22a57a8804d1f709e603` |

## 5. Analyse de `result_id` et `decode_id` (chemins de cache)

**Constat avant correctif (reproduit).** `GET /api/export?result_id=...` et `GET /api/decode/download?decode_id=...` construisaient `CACHE_DIR / f"{id}.xlsx"` (ou `.bin` + `.json`) sans valider l'identifiant. Reproduction avec `TestClient`, fichiers sentinelles créés par la sonde dans le répertoire temporaire, un niveau au-dessus du cache :

| Requête | Avant correctif | Après correctif |
| --- | --- | --- |
| `GET /api/export?result_id=../b2d_probe_secret` (fichier `b2d_probe_secret.xlsx` hors cache) | `200`, corps `SECRET-OUTSIDE-CACHE` | `404 {"detail":"Export failed"}` |
| `GET /api/export?result_id=<chemin absolu sans .xlsx>` | `200`, contenu du fichier | `404` |
| `GET /api/decode/download?decode_id=../b2d_probe_d` (`.bin` + `.json` hors cache) | `200`, contenu du `.bin` | `404` |
| `GET /api/export?result_id=../../../../etc/passwd` | `404` (pas d'extension `.xlsx`) | `404` |

**Criticité.** Lecture de fichiers hors du répertoire de cache : **réelle**, donc P1 (traversée de chemin, lecture seule). Portée limitée : export = fichiers se terminant par `.xlsx` ; download = paires `X.bin` + `X.json` lisibles par le processus ; le `Content-Disposition` utilise le `filename` du JSON. Pas d'écriture hors cache : l'écriture à l'export exige un `result_id` présent dans le cache mémoire (généré par le serveur). Pas d'injection de commande ni de SQL observée (aucun appel shell/DB avec ces valeurs). Le POST `/api/export` n'impose que `min_length=8`, donc `../abcdefg` passe aussi.

**Correctif minimal** (`backend/app/main.py`) : les identifiants sont toujours `uuid4().hex`. Une expression `[0-9a-f]{32}` (`_ID_RE`, `fullmatch`) est exigée ; sinon réponse `404` avec le même corps qu'un identifiant inconnu. Aucun changement de codec, de format ni de réponse pour un identifiant valide. Test : `test_api.py::test_path_traversal_ids_are_rejected` (échoue sans le correctif : `assert 200 == 404`, réussit avec).

## 6. Traçabilité des P2 des sprints précédents

| Origine | P2 | Statut | Détail |
| --- | --- | --- | --- |
| Sprint 1 (PR #4) | Port 8001 mal attribué à `api.ts` | Différé | Les replis `127.0.0.1:8001` existent bien dans `frontend/src/lib/api.ts` (l. 106, 114, 139) ; le README les documente. Pas de changement fonctionnel dans ce sprint. |
| Sprint 1 | Diagnostic `pydantic-core` trop affirmatif | Différé | Formulation du README inchangée (« vous n'êtes pas en Python 3.12 »). Trivial mais non vérifié sur d'autres causes. |
| Sprint 1 | Versions non épinglées | Corrigé (CI) | Actions épinglées par SHA, Python 3.12, Node 22 ; `requirements.txt` et `package-lock.json` déjà figés. |
| Sprint 1 | Syntaxe POSIX seule | Différé | README : exemples `source .venv/bin/activate`, `lsof`. Pas de test Windows. |
| Sprint 1 | Comptes de tests codés en dur | Corrigé | README renvoie vers ce document daté. |
| Sprint 3 (PR #6) | 422 non documenté | Corrigé | Lignes ajoutées à `docs/API.md`. |
| Sprint 3 | « Invalid XLS file » absent | Corrigé | Ajouté à `docs/API.md`. |
| Sprint 3 | `str(exc)` du décodage sondé avec données bidon seulement | Différé | Pas de fuzz de `/api/decode`. Les messages observés sont fixes ; changement de code hors périmètre. |
| Sprint 3 | Lignes vides parasites dans un test | Corrigé | Supprimées dans `test_api.py`. |
| Sprint 4 (PR #7) | `safeFetch` couvre seulement l'encodage | Différé | Changement fonctionnel frontend, hors périmètre. |
| Sprint 4 | Couverture mince (alerte decode, WARNING) | Différé | Tests frontend non ajoutés dans ce sprint. |
| Sprint 2 (PR #5) | Notes optionnelles (SHA implicite, ECC sur un seul cas, message d'erreur couplé) | Différé | Durcissement optionnel de tests. |
| Revue Sprint 3 | 500 non testés (`Export failed`, `Decoding failed`) | Différé | Documentés depuis le code uniquement. |

## 7. Testé / non testé, limites

Testé : suite backend (130), suite frontend (17), typecheck, build, bout en bout API pour 3 fixtures synthétiques, traversée de chemin sur les deux routes.

Non testé :

- aucun vrai document PDF/DOCX/DOC (fixtures synthétiques minuscules) ;
- aucun test navigateur, lecteur d'écran ou Windows ;
- aucun test avec gros fichiers (limite 5 Mo / 50 Mo non exercée par ce sprint), ni fuzz ;
- Python 3.14 non pris en charge (`pydantic-core`) ;
- le round-trip FAIL réel n'est pas reproductible par entrée (simulé par monkeypatch dans `test_api.py`) ;
- la CI ne couvre pas le serveur lancé (`uvicorn`) ni le frontend contre un vrai backend ;
- la protection de branche n'a pas été vérifiée ni modifiée.

Aucune synthèse biologique, aucun matériel, aucun changement de codec.
