---
name: recherche-procedure-electrique-compresseur

description: "Use when searching for electrical procedures (tension, alimentation, câblage, fusibles) for industrial compressors, especially Jenny. Covers voltage change (115V/230V), power supply verification, and electrical safety checks."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, électrique, maintenance, Jenny, tension, alimentation, procédure]

---

## Quand utiliser
- Un technicien demande la procédure pour changer la tension d'alimentation (ex: 115V ↔ 230V) sur un compresseur.
- Un utilisateur interroge sur la connexion électrique, la vérification de l'alimentation, ou le câblage d'un compresseur.
- Une recherche dans la documentation constructeur (ex: Jenny) est nécessaire pour des informations électriques.

## Patterns spécifiques
1. **Mots-clés à rechercher** :
   - `changement tension`, `115V 230V`, `alimentation électrique`, `câblage moteur`, `fusible`, `disjoncteur`, `sélecteur de tension`, `voltage change`, `power supply`, `electrical connection`, `Jenny`, `compresseur Jenny`.

2. **Sources prioritaires** :
   - Manuel d'installation/utilisation (Section "Installation", "Electrical", "Safety").
   - Schémas électriques (si indexés).
   - Fiches techniques ou guides de dépannage.

3. **Étapes de recherche** :
   a. **Recherche wiki** : Utiliser `search_wiki` avec les mots-clés ci-dessus.
   b. **Recherche chunks** : Si le wiki ne donne rien, utiliser `search_chunks` pour extraire des extraits des manuels PDF.
   c. **Vérification mémoire** : Consulter les procédures déjà documentées pour ce constructeur.
   d. **Clarification utilisateur** : Si aucune source ne contient l'information, demander à l'utilisateur d'ajouter les documents manquants.

4. **Extraction des informations** :
   - Toujours vérifier la **page du manuel** et le **numéro de page** pour citer correctement la source.
   - Noter les **prérequis** (ex: débrancher l'équipement, vérifier la compatibilité du réseau).
   - Identifier les **pièges** (ex: ne pas modifier la tension sans vérifier le sélecteur, risque de choc électrique).

## Pièges courants
- **Inversion des tensions** : Certains compresseurs ont un **sélecteur interne** (ex: cavalier ou interrupteur) pour choisir entre 115V et 230V. **Ne jamais forcer** le changement sans vérifier la position du sélecteur.
- **Compatibilité réseau** : Toujours vérifier que le réseau électrique du site correspond à la tension du compresseur (ex: un compresseur 230V ne peut pas fonctionner sur un réseau 115V sans modification).
- **Fusibles et disjoncteurs** : Certains modèles nécessitent de **changer les fusibles** lors du passage 115V ↔ 230V. Toujours vérifier la section "Electrical Data" du manuel.
- **Documentation incomplète** : Si la procédure n'est pas dans le manuel, elle peut être dans une **fiche technique séparée** ou un **guide d'installation spécifique**.

---

## Exemple d'application
**Demande utilisateur** : "Comment changer la tension d'alimentation entre 115V et 230V sur un compresseur Jenny ?"

**Actions TraceAI** :
1. Recherche dans le wiki avec les mots-clés `Jenny changement tension 115V 230V compresseur`.
2. Si rien, recherche dans les chunks avec `Jenny compresseur changement tension 115V 230V procédure`.
3. Vérification de la mémoire pour des procédures similaires.
4. Si aucune source ne contient l'information :
   - Réponse : "Aucun document indexé pour ce projet ne contient la procédure de changement de tension d'alimentation (115V/230V) pour les compresseurs Jenny."
   - Suggestion : Ajouter le manuel d'installation ou les fiches techniques électriques via **+ Ajouter des documents**.

**Citation des sources** : Toujours indiquer la page du manuel (ex: `[JennyCompressorManual.pdf, p.22]`).