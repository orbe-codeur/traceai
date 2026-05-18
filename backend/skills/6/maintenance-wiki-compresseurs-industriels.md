---
name: maintenance-wiki-compresseurs-industriels
description: "Use when ingesting, analyzing, or maintaining technical documentation for industrial compressors (Jenny, Atlas Copco, etc.) in a collaborative wiki environment."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [wiki, maintenance, compresseur, documentation, collaboration]
---

## Quand utiliser
- **Ingestion de manuels techniques** : Compresseurs Jenny, Atlas Copco GA37, ou autres modèles industriels.
- **Détection de contradictions** : Vérifier les incohérences entre sources (ex. : couples de serrage, pressions de service).
- **Mise à jour du wiki** : Ajouter ou corriger des procédures, échéances, ou responsables maintenance.
- **Création d'alertes** : Identifier les risques (ex. : maintenance non documentée, échéances dépassées).
- **Validation de conformité** : S'assurer que les pratiques locales (ex. : Metz B2) respectent les normes constructeur.

---

## Patterns spécifiques
1. **Contexte multi-sources** :
   - Toujours croiser les informations entre :
     - Mémoire persistante (ex. : `compresseur_backup_Metz_B2`).
     - Wiki (ex. : fiches techniques, procédures).
     - Manuels constructeur (ex. : Jenny Products Inc, Atlas Copco).
   - **Exemple** : Le couple de serrage des boulons de culasse du Jenny (6 ft-lb) doit être comparé aux pratiques locales (ex. : conversion en N·m).

2. **Gestion des échéances** :
   - **Maintenance préventive** :
     - Purge condensat : Quotidienne/hebdomadaire (selon environnement).
     - Tension courroie : Toutes les 50 heures.
     - Remplacement filtre à air : Toutes les 100 heures (ou plus en environnement poussiéreux).
     - Vérification niveau d'huile : Toutes les 500 heures.
   - **Backup (GA37)** : Aucune procédure documentée → **alerte prioritaire**.

3. **Détection des contradictions** :
   - **Conflits explicites** : `contested: true` dans le wiki.
   - **Conflits implicites** :
     - Absence de documentation pour un équipement critique (ex. : GA37).
     - Unités de mesure incohérentes (ex. : ft-lb vs N·m).
     - Responsables maintenance non référencés dans le wiki.

4. **Création d'alertes** :
   - **Sévérité** :
     - **high** : Équipement critique sans maintenance documentée (ex. : GA37).
     - **medium** : Informations manquantes mais non bloquantes (ex. : pression de service).
     - **low** : Problèmes administratifs (ex. : responsable non référencé).
   - **Format** :
     - Titre clair et descriptif.
     - Description avec **actions requises** et **références machines**.<br>
     - Sévérité justifiée.

5. **Mise à jour du wiki** :
   - **Frontmatter obligatoire** :
     ```yaml
     ---
     title: Nom de la machine
     machine_ref: REF_CONSTRUCTEUR
     constructeur: NomConstructeur
     created: YYYY-MM-DD
     updated: YYYY-MM-DD
     type: machine
     tags: [tag1, tag2]
     sources: [raw/sha256.pdf]
     confidence: high | medium | low
     contested: false
     contradictions: []
     ---
     ```
   - **Sections critiques** :
     - Spécifications techniques (pression max, couple de serrage).
     - Procédures de maintenance (fréquences, outils requis).
     - Responsables maintenance.
     - Liens vers les manuels sources.

---

## Pièges courants
- **Ignorer les équipements de backup** :
  Les compresseurs de backup (ex. : Atlas Copco GA37) sont souvent négligés dans la documentation. **Toujours les inclure** dans les analyses.
  - *Solution* : Créer une alerte si aucune procédure n'est documentée.

- **Unités de mesure ambiguës** :
  Les manuels américains utilisent des unités impériales (ft-lb, psi), tandis que les pratiques locales peuvent être métriques (N·m, bar).
  - *Solution* : **Convertir systématiquement** et documenter les deux unités dans le wiki.

- **Responsables maintenance non référencés** :
  La mémoire persistante peut contenir des informations non synchronisées avec le wiki.
  - *Solution* : **Vérifier et synchroniser** les responsables dans les fiches machines.

- **Conflits entre sources** :
  Les manuels constructeur peuvent contenir des erreurs ou des omissions (ex. : pression de service non précisée).
  - *Solution* : **Croiser avec la plaque constructeur** et documenter les incertitudes.

- **Échéances de maintenance non vérifiées** :
  Les fréquences de maintenance (ex. : purge condensat) peuvent être ignorées en pratique.
  - *Solution* : **Vérifier les logs de maintenance** et créer des alertes si les échéances sont dépassées.

---

## Exemple de workflow
1. **Ingestion d'un manuel** :
   - Utiliser `ingest-manuel-technique` pour extraire les spécifications et procédures.
   - Identifier les contradictions avec le wiki existant.

2. **Analyse des échéances** :
   - Utiliser `check_deadlines` pour lister les équipements avec des échéances dépassées.
   - Comparer avec les fréquences documentées dans le wiki.

3. **Mise à jour du wiki** :
   - Ajouter/modifier les fiches machines avec les nouvelles informations.
   - Mettre à jour le `updated` dans le frontmatter.

4. **Création d'alertes** :
   - Utiliser `create_alert` pour les problèmes critiques (ex. : maintenance non documentée).

5. **Sauvegarde des learnings** :
   - Créer ou mettre à jour un skill pour capitaliser sur les patterns émergents.