# Byte2DNA

![Uploading Gemini_Generated_Image_g529djg529djg529.jpeg…]()


**Byte2DNA** est un POC de stockage numérique sur ADN.

Il permet d’importer un fichier PDF ou DOCX, de convertir son contenu binaire en séquences ADN numériques composées de `A`, `C`, `G` et `T`, de contrôler des paramètres simples comme le taux GC et les homopolymères, de vérifier la reconstruction exacte du fichier par comparaison SHA-256, puis d’exporter les séquences dans un fichier XLSX destiné à préparer une future synthèse physique d’ADN.

Le projet est volontairement simple et expérimental : son objectif est de démontrer un workflow complet :

```text
File → Bytes → DNA → Bytes → File
```

avec reconstruction binaire exacte du fichier original.

## Objectifs du POC

- Import de fichiers `.pdf` et `.docx`
- Lecture binaire du fichier original
- Calcul SHA-256
- Compression optionnelle
- Encodage numérique vers ADN
- Fragmentation et indexation
- Contrôle du taux GC
- Contrôle des homopolymères
- Validation automatique du round-trip
- Export XLSX des séquences et métadonnées

## Principe de validation

Le critère principal du POC est :

```text
SHA256(original) == SHA256(reconstructed)
```

Si cette condition n’est pas satisfaite, l’encodage est considéré comme invalide.

## Limites

Byte2DNA est un prototype expérimental. Il ne garantit pas que les séquences produites soient directement compatibles avec les contraintes d’un prestataire de synthèse ADN. Les paramètres biologiques et de synthèse doivent être validés avant toute utilisation physique.
