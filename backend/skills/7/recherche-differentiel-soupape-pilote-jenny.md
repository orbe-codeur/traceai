---
name: recherche-differentiel-soupape-pilote-jenny

description: "Use when ingérant/répondant/analysant des questions techniques sur le différentiel de pression d'une soupape pilote sur un compresseur Jenny. Fournit la valeur indicative, la procédure de réglage et les pièges à éviter."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, soupape-pilote, differentiel-pression, Jenny, pressostat, maintenance]

---

## Quand utiliser
- **Besoin** : Obtenir la valeur du différentiel de pression d'une soupape pilote Jenny (différence entre pression de coupure et pression de redémarrage).
- **Contexte** : Répondre à une question technique, préparer une intervention de maintenance, ou vérifier un réglage.
- **Exemples de requêtes** :
  - "Quel est le différentiel de pression de la soupape pilote ?"
  - "Comment régler le différentiel de pression sur un compresseur Jenny ?"
  - "Quelle est la pression de coupure par défaut sur un Jenny modèle X ?"

---

## Étapes clés à suivre
1. **Recherche initiale** :
   - Utiliser `search_wiki` avec la requête : `soupape pilote differentiel de pression Jenny compresseur`.
   - Si le wiki ne contient pas l'information, utiliser `search_memory` pour vérifier si le constructeur est connu.

2. **Vérification des sources** :
   - Consulter le **JennyCompressorManual.pdf** (pages 26, 40) pour les valeurs par défaut et les procédures de réglage.
   - Vérifier les synthèses du wiki (ex. : `2026-05-19-comment-ajuster-le-regulateur-de-pression-soupape-pilote-sur.md`) pour les procédures détaillées.

3. **Extraction des données** :
   - Identifier le **barillet 'C'** comme élément de réglage du différentiel.
   - Noter que le manuel donne un **exemple typique de 30 psi** (ex. : 100-130 psi), mais que cette valeur n'est pas universelle.
   - Préciser que la valeur par défaut dépend du **modèle** et de l'**usage** du compresseur.

4. **Validation** :
   - Croiser les informations avec au moins **2 sources** (manuel + wiki ou mémoire).
   - Si une incohérence est détectée, signaler les contradictions et proposer une méthode de mesure (manomètre).

5. **Réponse finale** :
   - Fournir la valeur indicative (30 psi) **en précisant qu'il s'agit d'un exemple**.
   - Inclure la procédure de réglage et les pièges à éviter.
   - Orienter vers le manuel spécifique du modèle si nécessaire.

---

## Patterns spécifiques
1. **Requête utilisateur** :
   - Si la question contient des mots-clés comme `differentiel`, `soupape pilote`, `Jenny`, ou `pression`, déclencher ce skill.
   - Ignorer les questions sans lien avec Jenny ou les compresseurs (ex. : "differentiel de pression sur une pompe Grundfos").

2. **Gestion des valeurs par défaut** :
   - Toujours indiquer que le **30 psi** est un exemple et non une valeur universelle.
   - Proposer de rechercher le manuel spécifique du modèle si l'utilisateur le demande.

3. **Sécurité** :
   - Rappeler systématiquement les **précautions** :
     - Débrancher et vider le réservoir avant toute intervention.
     - Ne pas desserrer le barillet 'C' de plus d'un tour.
     - Utiliser un manomètre pour vérifier les pressions.

---

## Pièges courants
- **Inventer une valeur universelle** : Le différentiel de 30 psi est un exemple, pas une règle absolue. **Ne jamais affirmer qu'il s'agit de la valeur par défaut pour tous les modèles Jenny.**
- **Oublier de vérifier le modèle** : Toujours préciser que la valeur dépend du modèle et de l'usage (industriel/domestique).
- **Négliger les sources** : Ne pas se fier uniquement à la mémoire ou à un seul document. **Toujours croiser avec le manuel ou le wiki.**
- **Ignorer les pièges de réglage** : Un différentiel trop faible provoque un *chatter* de la soupape, et un différentiel trop élevé réduit l'efficacité du compresseur.

---

## Exemple de réponse type
```
Le differentiel de pression de la soupape pilote sur un compresseur Jenny est la difference entre la pression de coupure (cut-out) et la pression de redemarrage (cut-in).

**Valeur indicative** : Le manuel donne un exemple typique de **30 psi** (ex. : 100-130 psi), mais cette valeur n'est pas universelle. Elle depend du modele et de l'usage du compresseur.

**Reglage** : Utiliser le **barillet 'C'** pour ajuster le differentiel (sens horaire = augmentation, sens anti-horaire = diminution).

**Sources** : [JennyCompressorManual.pdf, p.40], [wiki/syntheses/2026-05-19-comment-ajuster-le-regulateur-de-pression-soupape-pilote-sur.md]
```