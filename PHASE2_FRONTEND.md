# TraceAI — Spécification Frontend Phase 2
> Pour le designer. Desktop uniquement. Refonte de Phase2IngestView.
> Un seul profil : le responsable fait l'ingestion ET pose les questions.

---

## Contexte technique

- **Framework** : Vue.js 3 Composition API + Vite + Tailwind CSS
- **Route existante** : `/project/:id/wiki-agent` (remplace Phase2IngestView actuelle)
- **API backend** : `http://localhost:8000` (voir endpoints ci-dessous)
- **Streaming** : Server-Sent Events sur `/agent-chat/stream`
- **Pas de mobile** : desktop uniquement, min-width 1200px

---

## Les 2 états principaux de la vue

La vue a deux états fondamentaux selon si des documents ont été ingérés :

```
État A : Projet vide          État B : Base de connaissances prête
┌─────────────────────┐       ┌────────────────────────────────────┐
│   Zone de dépôt     │  →    │  Tabs : Chat | Wiki | Graph | Alertes │
│   + questions       │       │  (la vue principale au quotidien)  │
│   + progression     │       └────────────────────────────────────┘
└─────────────────────┘
```

---

## État A — Ingestion (première fois ou ajout de docs)

### A1 — Zone de dépôt (empty state)

**Ce que l'utilisateur voit quand il arrive pour la première fois.**

Composants :
- Zone drag & drop centrale (grande, accueillante)
- Texte : *"Déposez vos documents techniques"*
- Sous-texte : *"PDF, Word, Excel — manuels, rapports, fiches techniques"*
- Bouton alternatif : "Parcourir les fichiers"
- Indicateur : nombre de documents déjà ingérés si > 0

### A2 — Liste des fichiers déposés

**Après dépôt, avant lancement.**

Composants :
- Liste des fichiers avec pour chaque fichier :
  - Icône selon type (PDF rouge, Excel vert, Word bleu)
  - Nom du fichier
  - Taille
  - Badge type détecté automatiquement : `Manuel constructeur` / `Rapport d'intervention` / `Inventaire pièces` / `Inconnu`
  - Bouton supprimer (×)
- Bouton principal : "Analyser les documents" → déclenche le scan rapide

> **Note pour le designer** : Le scan initial est rapide (0 LLM). L'utilisateur attend max 3-5 secondes.

### A3 — Questions de l'agent (IngestionPlannerAgent)

**L'agent a scanné et pose des questions pour clarifier.**

C'est le moment clé du flux. L'agent pose 3-4 questions avec des choix clairs.

Composants :
- En-tête : *"J'ai analysé [N] documents. Quelques questions avant de commencer."*
- Résumé de ce que l'agent a trouvé :
  ```
  📁 47 manuels constructeur
  📋 23 rapports d'intervention  
  📊 8 inventaires pièces
  ❓ 22 documents non identifiés
  ```
- **Carte question** (répétée pour chaque question) :
  - Texte de la question
  - 2 à 4 boutons-réponses (style pill/chip cliquable)
  - Option "Autre" → champ texte libre
  - Indicateur de progression : Question 1/3

Exemples de questions que l'agent peut poser :
- *"Ces documents concernent quel site ?"* → [Metz B2] [Grenoble] [Autre site]
- *"Les fichiers 'ORC-*.pdf' concernent quelle machine ?"* → [Compresseur Jenny] [Atlas Copco] [Je ne sais pas]
- *"Il y a 2 manuels Jenny (2019 et 2023). Lequel est la référence ?"* → [2023 (le plus récent)] [2019 (validé terrain)] [Les deux]

> **Important pour le design** : Ces questions doivent être rassurantes, pas intimidantes. Le collègue non-technicien ne doit pas se sentir bloqué. Option "Je ne sais pas" toujours disponible.

### A4 — Plan d'ingestion (confirmation avant exécution)

**L'agent montre ce qu'il va faire. L'utilisateur valide avant de lancer.**

Composants :
- Titre : *"Voici comment je vais traiter vos documents"*
- Tableau de plan :
  | Document | Type | Stratégie | Priorité |
  |---|---|---|---|
  | jenny-manual-2023.pdf | Manuel constructeur | Source principale | 🔴 Élevée |
  | jenny-manual-2019.pdf | Manuel constructeur | Archive | 🟡 Moyenne |
  | rapport-*.pdf (8 fichiers) | Rapport d'intervention | Extraction date + technicien | 🟡 Moyenne |
  | inconnus (4 fichiers) | Non identifié | Analyse manuelle requise | 🟢 Basse |
- Avertissements si pertinent :
  - ⚠️ *"4 fichiers non lisibles (scannés sans OCR)"*
  - ℹ️ *"2 doublons détectés — le plus récent sera conservé"*
- Durée estimée : *"~12 minutes"*
- Bouton principal : **"Lancer l'ingestion"**
- Bouton secondaire : "Modifier" (retour aux questions)

### A5 — Progression en temps réel

**L'ingestion tourne. L'utilisateur voit ce qui se passe.**

Composants :
- Barre de progression globale (ex: 34/80 documents)
- Liste des documents avec statut par fichier :
  - ⏳ En attente (gris)
  - 🔄 En cours (bleu animé)
  - ✅ Ingéré (vert)
  - ❌ Erreur (rouge + message)
- **Log streaming** (zone scrollable) : ce que l'agent dit en temps réel
  ```
  → Analyse jenny-manual-2023.pdf...
  → 6 pages machine créées
  → Couple de serrage : 6 ft-lb [p.48] ✅
  → Entité détectée : Jenny Products Inc.
  → Traitement rapport-2023-05-15.pdf...
  ```
- Possibilité de continuer à utiliser l'app pendant l'ingestion (tabs accessibles)
- Notification quand terminé : toast + badge sur l'onglet

---

## État B — Base de connaissances prête (vue quotidienne)

**C'est l'état principal après ingestion. 4 onglets.**

```
┌──────────────────────────────────────────────┐
│  [Chat ●]  [Wiki]  [Graph]  [Alertes (2)]     │
│  ← onglets actifs, badge sur alertes          │
└──────────────────────────────────────────────┘
```

---

### Onglet Chat (par défaut, usage quotidien)

**Le collègue pose ses questions ici.**

Layout : 2 colonnes
- **Gauche (70%)** : conversation
- **Droite (30%)** : contexte / sources (peut être collapsible)

**Zone conversation :**
- Messages utilisateur : bulles à droite, fond coloré
- Messages agent : bulles à gauche, fond neutre
- Sur chaque message agent :
  - Texte avec rendu markdown
  - **Badges de confiance** sur chaque valeur vérifiable :
    - ✅ `6 ft-lb` `[jenny-manual p.48]` → vérifié, clic ouvre la source
    - ⚠️ `8 ft-lb` → non vérifié dans les sources, à confirmer
  - Indicateur d'itérations : *"3 sources consultées"*
  - Bouton "Voir les sources" → ouvre le panneau droit
- Affichage **streaming** : le texte apparaît token par token
- Indicateur de tools en cours : *"🔍 Recherche dans le wiki..."*

**Zone saisie :**
- Input pleine largeur
- Bouton envoi
- Chips de suggestions contextuelles : *"Planning maintenance"* | *"Couple de serrage"* | *"Dernière intervention"*

**Panneau droit — Sources :**
- Affiché quand l'agent répond
- Liste des sources utilisées pour cette réponse
- Pour chaque source : titre doc + page + extrait pertinent

**Questions de clarification :**
Si l'agent demande `ask_clarification`, afficher dans la conversation :
- Texte de la question en bulle agent
- Boutons-réponses sous la question (pas dans l'input, dans le flux de conversation)
- Même style que A3

---

### Onglet Wiki

**Naviguer dans la base de connaissances construite.**

Layout : 2 colonnes
- **Gauche (25%)** : navigation
- **Droite (75%)** : contenu de la page

**Navigation gauche :**
- Sélecteur de machine (dropdown ou tabs verticaux)
  - 🔧 Jenny Compressor
  - 🔧 Atlas Copco GA55
  - ... (scroll si > 5)
- Sections pour la machine sélectionnée :
  - 📄 Vue d'ensemble
  - ⚙️ Spécifications
  - 🔄 Maintenance
  - 🔗 Entités liées
  - 📚 Sources
  - 💡 Concepts
- Barre de recherche dans le wiki

**Contenu principal droit :**
- Titre de la page
- Date dernière mise à jour
- Contenu markdown rendu
- **Wikilinks** `[[jenny-compressor]]` rendus comme badges cliquables :
  ```
  → 🔧 Jenny Compressor    (clic → navigue vers la page)
  ```
- **Tableau spécifications** (quand wiki structuré sera implémenté) :
  | Paramètre | Valeur | Unité | Source | Confiance |
  |---|---|---|---|---|
  | Couple culasse | 6 | ft-lb | jenny p.48 | ✅ HIGH |
  | Pression coupure | 125-175 | psi | jenny p.41 | ✅ HIGH |
- Bouton "Éditer" (pour corrections manuelles futures)
- Bouton "Voir dans le graph" → focus ce nœud dans l'onglet Graph

---

### Onglet Graph

**Visualisation des relations entre machines, entités, concepts.**

Composants :
- **iframe ou vue intégrée** du `graph.html` vis.js (déjà généré par le backend)
- Barre de contrôle au-dessus :
  - Filtres : [Machines] [Entités] [Concepts] [Tout]
  - Bouton "Regénérer le graph"
  - Bouton "Plein écran"
- Panneau latéral au clic sur un nœud :
  - Titre + type du nœud
  - Extrait de la page wiki
  - Lien "Voir la page complète" → navigue vers Wiki tab

---

### Onglet Alertes

**Problèmes détectés + jobs planifiés.**

Layout : 2 sections

**Section Alertes actives :**
- Carte par alerte :
  - Pastille sévérité : 🔴 Critique / 🟠 Haute / 🟡 Moyenne / 🟢 Basse
  - Titre
  - Machine concernée
  - Description courte
  - Date de détection
  - Bouton "Ignorer"
- État vide : *"Aucune alerte active — votre wiki est cohérent ✅"*

**Section Jobs planifiés (Cron) :**
- Bouton "Nouveau job" → modal simple :
  - Nom du job
  - Mode : [Alerte] [Analyse] [Chat]
  - Instruction pour l'agent (textarea)
  - Fréquence : [Toutes les nuits] [Toutes les semaines] [Toutes les heures] [Personnalisé]
- Liste des jobs existants :
  - Nom + fréquence + prochain run
  - Dernier résultat (extrait 100 chars)
  - Boutons : ▶️ Lancer maintenant | ⏸️ Pause | 🗑️ Supprimer

---

## Ce qu'il me manque pour finaliser la spec

> Questions pour le designer avant de commencer les maquettes.

**1. Traitement visuel de la confiance**
Comment montrer ✅ vérifié vs ⚠️ à vérifier dans le texte de réponse ?
- Option A : Badge coloré inline sur chaque valeur (vert/orange)
- Option B : Soulignement coloré (vert = vérifié, orange = incertain)
- Option C : Icône en fin de phrase + tooltip au survol
- Option D : Panneau latéral séparé, texte neutre dans la réponse

**2. Navigation machines avec 20+ machines**
Si le client a 50 machines :
- Option A : Dropdown searchable dans la sidebar wiki
- Option B : Page d'accueil wiki avec grille de machines (comme des cartes)
- Option C : Barre de recherche globale dans le wiki

**3. Wikilinks dans les réponses chat**
Quand l'agent dit "voir [[jenny-compressor]]" :
- Option A : Chip/badge cliquable qui ouvre l'onglet Wiki
- Option B : Lien souligné style Wikipedia
- Option C : Hover card avec aperçu de la page

**4. Ingestion pendant l'usage**
Si l'utilisateur ajoute des docs pendant qu'il travaille (pas empty state) :
- Bouton "Ajouter des documents" permanent dans le header ?
- Ou seulement accessible via un tab "Ingestion" ?

**5. Indicateur de santé globale**
Un badge/widget quelque part qui montre l'état du wiki :
- Nombre de machines, documents, pages
- Dernière ingestion
- Alertes actives (nombre)
- Ou c'est trop d'info dans l'UI ?

---

## Endpoints backend disponibles

```
POST /api/projects/{id}/agent-chat/stream  → Chat streaming SSE
POST /api/projects/{id}/wiki-ingest        → Lancer ingestion
GET  /api/projects/{id}/wiki-health        → Santé wiki
GET  /api/projects/{id}/wiki-overview      → Page overview
GET  /api/projects/{id}/graph.html         → Visualisation graph
POST /api/projects/{id}/build-graph        → Regénérer graph
POST /api/projects/{id}/wiki-heal          → Auto-réparer wiki
GET  /api/projects/{id}/memory             → Mémoire persistante
GET  /api/projects/{id}/skills             → Skills disponibles
POST /api/projects/{id}/cron               → Créer job cron
GET  /api/projects/{id}/cron               → Lister jobs cron
POST /api/cron/{id}/trigger                → Déclencher job
GET  /api/projects/{id}/alerts             → Alertes actives
```

---

## Contraintes design

- Tailwind CSS — pas de librairie UI externe imposée
- Cohérence avec Phase 1 existante (même TopBar, même palette)
- Pas d'animations lourdes — l'app est fonctionnelle avant d'être belle
- Le streaming SSE doit être fluide — pas de re-renders qui sautent
- Accessibilité minimale : contrastes suffisants, labels sur les inputs
