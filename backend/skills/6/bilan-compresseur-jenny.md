---
name: "bilan-compresseur-jenny"
description: "Use when building a complete technical assessment for a Jenny compressor, including specifications, maintenance plans, critical parts identification, and backup equipment recommendations."
version: "1.0.0"
author: "TraceAI"
metadata: {"hermes": {"tags": ["compresseur", "jenny", "maintenance", "specs", "backup"]}}
---
## Quand utiliser
- Pour générer un **bilan complet** d'un compresseur Jenny (spécifications, maintenance préventive, pièces critiques).
- Pour **intégrer un nouvel équipement de backup** (ex : Atlas Copco GA37) dans la base de connaissances.
- Pour **synthétiser des données techniques** issues de manuels ou de rapports.

## Étapes clés (workflow émergent)
1. **Recherche initiale** :
   - Utiliser `search_wiki` avec des requêtes ciblées (`specs techniques`, `maintenance préventive`, `pièces critiques`).
   - Croiser avec `search_memory` pour vérifier les conventions du site (ex : responsable maintenance, équipements existants).

2. **Extraction des données** :
   - Identifier les **spécifications techniques** (type, pression, couple de serrage, normes électriques).
   - Lister les **procédures de maintenance** (fréquences, outils requis, sécurité).
   - Recenser les **pièces critiques** (risques, fréquences de vérification/remplacement).

3. **Validation et lacunes** :
   - Signaler les **valeurs manquantes** (ex : pression de service exacte) et proposer des actions correctives (vérifier la plaque constructeur).
   - Vérifier les **unités** (ex : conversion ft-lb → Nm si nécessaire).

4. **Intégration des équipements supplémentaires** :
   - Mémoriser les **nouveaux équipements** (ex : backup Atlas Copco GA37) via `save_memory`.
   - Mettre à jour les **pages wiki** ou créer des liens croisés si pertinent.

5. **Formatage du résultat** :
   - Structurer la réponse en **sections claires** (spécs, maintenance, pièces critiques, backup).
   - **Citer toutes les sources** (fichiers, pages wiki, mémoire).
   - Proposer des **prochaines étapes** (ex : inspection sous 50h, vérification de la plaque constructeur).

## Patterns spécifiques
- **Couple de serrage** : Toujours vérifier l'unité (ft-lb vs Nm) et la source (manuel Jenny, p.48).
- **Maintenance préventive** : Croiser les fréquences (quotidienne, 50h, 100h, 500h) avec les procédures du manuel.
- **Pièces critiques** : Associer chaque pièce à un **risque** et une **fréquence de vérification** pour prioriser les actions.
- **Backup equipment** : Mémoriser systématiquement le nouvel équipement avec son rôle et le responsable associé.

## Pièges courants
- **Incohérences d'unités** : Ne pas convertir les couples de serrage (ex : 6 ft-lb → ~8.1 Nm) peut induire en erreur.
- **Sources incomplètes** : Ignorer les lacunes (ex : pression de service absente) et ne pas proposer de solution pour les combler.
- **Oubli de citation** : Toujours associer les données à leur source pour éviter les erreurs de traçabilité.
- **Mauvaise intégration** : Ne pas mémoriser les nouveaux équipements (ex : GA37) dans la base de connaissances.