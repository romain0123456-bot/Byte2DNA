# Preuve native du dashboard — essai b106c1d0-11e8-440b-aeee-f9af91cb2eb8

## Périmètre et provenance

Ce document accompagne une unique PR de test vers `main` du dépôt
`romain0123456-bot/Byte2DNA`, sans fusion. Inspection effectuée le 16 octobre
2026 sur la base `e745638ed50a2ec4650b22a57a8804d1f709e603`, également renvoyée
par l'API GitHub pour `main`. Le changement autorisé porte uniquement sur ce
fichier : aucune modification applicative, de dépendance, de secret, de workflow,
d'infrastructure ou de configuration CI. Le répertoire préexistant non suivi
`graft/` est exclu de la livraison.

Sources inspectées : `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`,
`frontend/package.json`, `backend/pytest.ini`, `backend/requirements.txt` et
`.github/workflows/lot5-qualification.yml`. Les documents existants utilisent
du Markdown en français, avec des sections, références de fichiers et blocs de
commandes ; ce document conserve ces conventions.

## Identifiants natifs effectivement connus

| Objet | Identifiant observé |
| --- | --- |
| Mission, fournie par la tâche | `de1d9b9a-0e70-4728-9923-b32da6974b30` |
| Essai, fourni par la tâche | `b106c1d0-11e8-440b-aeee-f9af91cb2eb8` |
| Sprint, confirmé par le coordinateur | `sprint-1` |
| Demande backend, confirmée par le coordinateur | `c9a5d519-fe60-4586-89ba-f6114de0a12f` |
| Tâche | `task_b9b93fde5b75` |
| Dispatch, retourné par `orca orchestration check` | `ctx_3108113544ad` |
| Run, retourné par `orca orchestration check` | `run_fceb3d74cdb8` |
| Terminal développeur | `term_dac61179-8a97-47dc-8afe-27fc2586f0a7` |
| Terminal coordinateur fourni au dispatch | `term_2f054500-811d-4e0d-88d2-d0cba43c078d` |
| Rôle | `developer` |

L'admission a été demandée avec `orca orchestration ask` avant toute inspection
du dépôt. Le coordinateur a d'abord signalé `connection_lost`, `user_owned` et
`retainedReason=user_takeover` : le travail est resté en attente. Une seconde
réponse native a ensuite confirmé la demande `active`, les mêmes tâche,
dispatch et session, `execution_sprint_limit=1` et `scheduling_paused=false`,
et autorisé la poursuite de cette tâche sans nouvelle allocation. Cette
confirmation provient du coordinateur consulté via le backend ; elle ne
constitue pas une inspection visuelle indépendante de l'UI par le développeur.
Aucune réattribution ou fermeture de la session conservée n'a été réalisée.

## Commandes déclarées, sans nouvelle validation applicative

Le README déclare les commandes suivantes :

```sh
cd backend
python -m pytest
```

```sh
cd frontend
npm test
npm run typecheck
npm run build
```

`frontend/package.json` associe ces commandes à `vitest run`, `tsc --noEmit`
et `next build`. Le README rapporte historiquement 111 tests backend et 15
tests frontend réussis, ainsi que typecheck et build sans erreur. Ces résultats
sont des déclarations du README, pas des exécutions de cet essai. Aucun serveur,
test applicatif, build ou installation de dépendances n'a été lancé ici.

Le seul workflow suivi observé, `LOT5 qualification`, se déclenche sur `push`
et `pull_request`, sous `ubuntu-latest` avec Python 3.12, un délai de cinq
minutes et `permissions: contents: read`. Sa commande Python découvre
`qualification/lot5/tests` avec `unittest`, exige au moins quatre tests et
échoue si leur résultat est négatif. Il ne lance pas les commandes applicatives
ci-dessus.

## Résultats effectivement observés avant publication

L'équivalent local du bloc de qualification a été exécuté avec
`PYTHONDONTWRITEBYTECODE=1 python3` :

```python
import unittest
suite = unittest.defaultTestLoader.discover('qualification/lot5/tests')
if suite.countTestCases() < 4:
    raise SystemExit('At least four actual feature tests are required')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
```

Résultat observé : 12 tests découverts, `Ran 12 tests in 0.001s`, `OK`, code
de sortie 0. L'interpréteur local était Python 3.14.6 sur macOS, différent du
Python 3.12 Linux déclaré en CI. Ce résultat qualifie uniquement ces tests
locaux sur la base inspectée ; il ne prouve aucune CI hébergée sur le futur
HEAD documentaire.

GitHub a renvoyé `viewerPermission=ADMIN`, la branche par défaut `main` et
`protected=false` pour cette branche. Ce constat n'établit ni l'absence de
rulesets, ni les permissions d'une autre identité, ni l'approbation d'une revue.
Aucun contournement de protection n'est autorisé ou utilisé.

## Limites et preuves restant à rattacher

Au moment de la rédaction, la PR et son SHA final n'existent pas encore : leurs
valeurs exactes seront transmises au coordinateur après publication et lecture
GitHub, sans prétendre inscrire dans ce commit son propre SHA. Il reste à
vérifier le diff distant limité à ce fichier et les checks attachés au HEAD
publié. Aucun résultat CI hébergé, aucune revue indépendante et aucune preuve
visuelle UI ne sont établis par ce document. Les permissions effectives pour
Actions et les éventuelles règles supplémentaires n'ont pas été auditées.

Une CI verte LOT5 ne couvrirait pas les tests backend/frontend, le build,
le parcours navigateur ou une synthèse ADN physique. Toute modification du
HEAD impose une nouvelle revue et une nouvelle vérification CI de ce SHA.
La PR reste une PR de test, sans fusion.
