---
name: recherche-valeur-manquant-dans-docs-constructeur

description: "Use when the exact technical value (pressure, torque, flow rate, etc.) is not found in indexed documents, but the procedure or context is documented."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [recherche, documentation, constructeur, valeur-manquante, procédure]

---

## Quand utiliser
Ce skill s'applique lorsque :
- La valeur technique exacte (ex: pression de coupure, couple de serrage, débit) n'est pas trouvée dans les documents indexés.
- Une procédure ou un contexte est disponible pour expliquer comment obtenir ou ajuster cette valeur.
- L'utilisateur a besoin d'une réponse claire sur l'absence de la valeur et des pistes pour la trouver.

## Patterns spécifiques
1. **Recherche systématique** :
   - Utiliser `search_wiki` avec des mots-clés précis (ex: "[machine] [pièce] [valeur recherchée]").
   - Croiser les résultats avec les synthèses et procédures associées.

2. **Analyse des limites des documents** :
   - Vérifier si les documents indexés contiennent des **procédures** ou des **contexte** liés à la valeur manquante.
   - Identifier les **sources officielles** (manuel constructeur, plaque signalétique) où la valeur devrait être indiquée.

3. **Communication claire** :
   - Informer l'utilisateur que la valeur n'est pas disponible dans les documents indexés.
   - Proposer des **alternatives concrètes** pour obtenir la valeur :
     - Consulter le **manuel constructeur** (pages spécifiques si disponibles).
     - Vérifier la **plaque signalétique** de la machine.
     - Contacter le **support technique du constructeur**.
     - Utiliser un **manomètre ou outil de mesure** pour vérifier la valeur in situ (si applicable).

4. **Documentation des pistes** :
   - Enregistrer dans la mémoire du projet les pistes identifiées pour une réutilisation future.

## Pièges courants
- **Supposer que la valeur est dans le manuel** sans vérifier les pages spécifiques.
- **Oublier de proposer des alternatives** pour obtenir la valeur manquante.
- **Confondre procédure et valeur** : Une procédure d'ajustement n'est pas une valeur par défaut.
- **Ne pas documenter les pistes** : Risque de perdre du temps à refaire la même recherche.

---

## Exemple d'application
**Cas** : Pression de coupure de la soupape pilote d'un compresseur Jenny.
**Résultat** :
- Le wiki contient des procédures pour ajuster la pression de coupure, mais **pas la valeur exacte**.
- La valeur doit être trouvée dans le **JennyCompressorManual.pdf** ou sur la **plaque signalétique**.
**Action** :
- Informer l'utilisateur de l'absence de la valeur dans les documents indexés.
- Lui proposer de consulter le manuel constructeur ou de contacter le support Jenny.
- Mettre à jour la mémoire du projet avec les pistes identifiées.