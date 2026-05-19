---
name: audit-maintenance-compresseurs-industriels

description: "Use when performing a systematic maintenance audit for industrial compressors, including checking deadlines, contradictions in technical documentation, and compliance with manufacturer specifications."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [audit, maintenance, compresseur, industrial, documentation, deadlines]

---

## Quand utiliser
Ce skill est déclenché lors d'un **audit complet de maintenance** pour des compresseurs industriels, notamment pour :
- Vérifier les **échéances de maintenance** (purge, tension courroie, filtre à air, huile, etc.).
- Identifier les **contradictions** dans les documentations techniques (wiki, manuels, rapports).
- Détecter les **lacunes** (ex. : pression de service manquante, unités non standardisées).
- Générer des **alertes** pour les risques critiques (ex. : backup non documenté, procédures manquantes).
- **Corréler les données** entre machines principales et backup (ex. : Jenny vs. Atlas Copco GA37).

Ce skill est particulièrement utile pour les sites multi-machines comme **Metz, Atelier B2**, où plusieurs compresseurs (Jenny, Atlas Copco GA37) coexistent.

---

## Patterns spécifiques

### 1. **Vérification des échéances de maintenance**
- **Sources** : Wiki (pages `maintenance-preventive-orc`, `controle-tension-courroie`), rapports de maintenance, manuels constructeurs.
- **Actions** :
  - Extraire les fréquences recommandées (ex. : purge quotidienne, vérification courroie toutes les 50h).
  - Comparer avec les **dernières interventions enregistrées** (via `check_deadlines`).
  - Identifier les **retards** ou **absences de suivi**.
- **Piège** : Confondre les fréquences en **heures de fonctionnement** vs. **jours calendaires** (ex. : purge quotidienne vs. toutes les 50h).

### 2. **Détection des contradictions dans le wiki**
- **Critères** :
  - Vérifier le champ `contested: true` dans les pages wiki.
  - Croiser les informations entre **pages machines**, **procédures**, et **standards** (ex. : `NEC-Article-422-4` pour les normes électriques).
- **Exemple de contradiction** :
  - Couple de serrage en **ft-lb** vs. **Nm** (standard européen).
  - Pression de service absente vs. mentionnée sur la plaque constructeur.
- **Outils** : Utiliser `search_wiki` avec des requêtes ciblées (ex. : `machine_ref:jenny-compressor AND contested:true`).

### 3. **Analyse des machines liées (backup/principal)**
- **Cas d'usage** : Sites comme Metz (Atelier B2) avec un compresseur **Jenny** (principal) et un **Atlas Copco GA37** (backup).
- **Actions** :
  - Vérifier si les **procédures de bascule** sont documentées.
  - S'assurer que les **spécifications techniques** (pression, couple, huile) sont **compatibles** entre les deux machines.
  - **Risque** : Appliquer des procédures inadaptées en cas de panne (ex. : utiliser la pression max du Jenny sur le GA37).
- **Piège** : Négliger la documentation du backup, considéré comme "secondaire".

### 4. **Génération d'alertes structurées**
- **Critères d'alerte** :
  - **Haute sévérité** : Backup non documenté, échéances critiques dépassées (ex. : huile non vérifiée depuis 600h).
  - **Moyenne sévérité** : Unités non standardisées, pression de service manquante.
- **Format** :
  - `title`: Description concise du problème.
  - `description`: Détails techniques et risques associés.
  - `severity`: high/medium.
  - `machine_ref`: Référence de la machine concernée (ex. : `jenny-compressor`, `compresseur_backup_Metz_B2`).
- **Outils** : Utiliser `create_alert` pour chaque alerte identifiée.

### 5. **Correction des lacunes documentaires**
- **Actions post-audit** :
  - **Ingestion de manuels** : Utiliser `ingest-manuel-compresseur` ou `ingest-compresseur` pour compléter les données manquantes (ex. : manuel Atlas Copco GA37).
  - **Mise à jour du wiki** : Ajouter les spécifications manquantes (ex. : pression de service, conversion Nm/ft-lb).
  - **Création de procédures** : Documenter les étapes de bascule entre machines (ex. : Jenny → GA37).

---

## Pièges courants

1. **Confondre les unités de mesure** :
   - Exemple : 6 ft-lb ≈ 8.1 Nm. Toujours convertir pour éviter les erreurs de serrage.
   - **Solution** : Ajouter une note dans le wiki avec la conversion.

2. **Négliger le backup** :
   - Le compresseur de secours est souvent moins documenté, alors qu'il peut être **critique** en cas de panne.
   - **Solution** : Auditer systématiquement les deux machines (principal + backup).

3. **Oublier les normes de sécurité** :
   - Exemple : Respect de l'article **NEC-Article-422-4** pour les installations électriques.
   - **Solution** : Croiser les procédures avec les standards (ex. : `norme-securite-electrique.md`).

4. **Sous-estimer les lacunes documentaires** :
   - Une pression de service manquante ou une fréquence de maintenance non suivie peut entraîner des **pannes coûteuses**.
   - **Solution** : Traiter les alertes **immédiatement** et prioriser les corrections.

5. **Ne pas corréler les données entre machines** :
   - Exemple : Appliquer la pression max du Jenny sur le GA37 sans vérification.
   - **Solution** : Documenter les **spécifications communes** et les **différences** dans une page dédiée (ex. : `compresseurs-Metz-B2.md`).

---

## Workflow recommandé
1. **Lancer l'audit** : Utiliser `check_deadlines` et `search_wiki` pour collecter les données.
2. **Analyser les contradictions** : Identifier les `contested: true` et les lacunes.
3. **Générer les alertes** : Créer une alerte pour chaque risque critique via `create_alert`.
4. **Prioriser les actions** : Corriger d'abord les alertes **haute sévérité** (ex. : backup non documenté).
5. **Documenter les corrections** : Mettre à jour le wiki ou ingérer de nouveaux manuels si nécessaire.
6. **Automatiser** : Sauvegarder ce skill pour réutiliser le workflow sur d'autres sites.