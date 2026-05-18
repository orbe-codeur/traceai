---
name: ingest-compresseur
description: Use when ingesting compressor manuals or industrial PDF documents
version: 1.0.0
author: TraceAI
metadata: {"hermes": {"tags": ["ingestion", "compresseur", "manuel", "pdf"]}}
archived: true
---
## Quand utiliser
Lors de l'ingestion de manuels de compresseurs industriels (Jenny, Atlas Copco, etc.)

## Patterns spécifiques
1. Vérifier d'abord si un wiki existe pour la machine concernée
2. Classifier comme manual_constructor si le document vient du fabricant
3. Extraire les spécifications techniques en priorité (pression, débit, couples de serrage)

## Pièges courants
- Les PDF scannés nécessitent OCR — utiliser doc_type: scanned_handwritten
- Les manuels multi-langues : ignorer les sections non-françaises
