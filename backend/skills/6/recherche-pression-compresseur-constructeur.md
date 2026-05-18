---
name: recherche-pression-compresseur-constructeur
description: "Use when searching for the maximum service pressure of a compressor by checking the manufacturer's plate or technical documentation. Handles cases where the value is missing or requires on-site verification."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [compresseur, pression, plaque-constructeur, maintenance]
---

## Quand utiliser
- Lorsqu'un technicien ou un agent doit **identifier la pression maximale de service** d'un compresseur.
- Lorsque la valeur est **absente des manuels extraits** mais indiquée sur la **plaque constructeur**.
- Pour **structurer une recherche** en combinant :
  - Wiki interne (manuels, synthèses).
  - Vérification physique sur site (plaque constructeur).
  - Cross-check avec les spécifications du constructeur.

## Étapes clés
1. **Recherche initiale** :
   - Utiliser `search_wiki` avec des mots-clés comme :
     - `compresseur [NOM_MODELE] pression maximale service`
     - `plaque constructeur [NOM_MODELE] pression`
     - `manual [NOM_MODELE] max pressure`
   - Vérifier les pages machines, manuels, et synthèses dans le wiki.

2. **Analyse des résultats** :
   - Identifier si la valeur est **explicitement mentionnée** dans le wiki.
   - Repérer les **références à la plaque constructeur** (ex: "voir plaque constructeur").
   - Noter les **valeurs partielles** (ex: pression de coupure de soupape pilote).

3. **Gestion des lacunes** :
   - Si la valeur est absente :
     - **Planifier une vérification sur site** (plaque constructeur).
     - **Contacter le responsable maintenance** pour confirmation.
     - **Documenter la lacune** dans le wiki avec une note claire.
   - Si la valeur est ambiguë (unité non précisée) :
     - Demander une **confirmation de l'unité** (psi, bars, kPa).

4. **Validation et mise à jour** :
   - Une fois la valeur obtenue :
     - Mettre à jour le wiki avec la valeur exacte et sa source.
     - Créer une **fiche technique rapide** si nécessaire.
     - Notifier le responsable maintenance (ex: Thomas Dubois pour Metz B2).

## Patterns spécifiques
- **Cas 1 : Valeur absente mais référence à la plaque constructeur**
  → **Action** : Planifier une vérification physique. Exemple :
  ```
  Compresseur Jenny : Pression max service → "voir plaque constructeur" [Jenny Compressors — Manuel d'installation et maintenance](wiki).
  → À vérifier sur site (Atelier B2, Metz).
  ```

- **Cas 2 : Valeur partielle disponible (ex: soupape pilote)**
  → **Action** : Utiliser comme **limite temporaire** et marquer comme "non définitive". Exemple :
  ```
  Pression de coupure soupape pilote : 125–175 psi [overview](wiki/overview.md).
  → À confirmer avec la pression max de service.
  ```

- **Cas 3 : Unité non précisée**
  → **Action** : Demander une clarification ou vérifier la plaque constructeur. Exemple :
  ```
  Unité de pression non confirmée dans le manuel. Vérifier sur la plaque constructeur (psi/bars/kPa).
  ```

## Pièges courants
- **Confondre pression de coupure de soupape pilote et pression max de service** :
  - La soupape pilote se déclenche **avant** d'atteindre la pression max de service. Ne pas l'utiliser comme référence principale.
  - *Exemple* : 125–175 psi pour la soupape pilote ≠ pression max de service.

- **Négliger la vérification physique** :
  - Toujours **privilégier la plaque constructeur** comme source ultime. Les manuels peuvent omettre des détails.

- **Oublier de documenter les lacunes** :
  - Si la valeur est absente, **noter clairement** dans le wiki pour éviter des recherches répétées.

- **Ignorer les unités** :
  - Toujours confirmer l'unité (psi, bars, kPa) pour éviter des erreurs d'interprétation.

## Exemple de workflow complet
1. **Recherche** :
   ```
   search_wiki("compresseur Jenny pression maximale service")
   ```
   → Résultat : Valeur absente, référence à la plaque constructeur.

2. **Planification** :
   - Contacter Thomas Dubois pour organiser la vérification sur site.
   - Préparer une procédure de relevé (ex: photo de la plaque, relevé manuel).

3. **Validation** :
   - Une fois la valeur obtenue :
     ```
     save_memory("compresseur_jenny_pression_max", "175 psi")
     ```
   - Mettre à jour le wiki :
     ```
     Jenny Compressors — Spécifications techniques :
     - Pression max service : 175 psi [plaque constructeur, vérifiée le 2026-05-18].
     ```

4. **Notification** :
   - Informer Thomas Dubois et l'équipe maintenance.

## Sources typiques
- Manuels techniques (PDF ou wiki).
- Plaques constructeur (sur site).
- Synthèses internes (overview, fiches techniques).
- Retours terrain (comptes-rendus de maintenance).

## Outils associés
- `search_wiki` : Pour rechercher dans la base de connaissances.
- `ask_clarification` : Pour demander une confirmation ou une action à un humain.
- `save_memory` : Pour mémoriser la valeur une fois validée.