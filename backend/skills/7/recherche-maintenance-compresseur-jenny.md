---
name: recherche-maintenance-compresseur-jenny
description: "Use when ingérant/répondant/analysant des questions sur la maintenance d'un compresseur Jenny et que le wiki n'est pas encore indexé."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [maintenance, compresseur, Jenny, wiki, vidange]
---

## Quand utiliser
- Quand l'utilisateur demande des informations sur la maintenance d'un compresseur Jenny (ex: vidange d'huile, pression de coupure, ventilation, etc.).
- Quand le wiki ne retourne **aucun résultat** après plusieurs tentatives de recherche.

## Patterns spécifiques
1. **Recherche initiale** : Toujours commencer par une requête précise dans le wiki (ex: `"vidange huile compresseur Jenny"`).
2. **Recherche élargie** : Si la première requête échoue, élargir avec des mots-clés génériques (ex: `"maintenance compresseur Jenny"`, `"vidange huile compresseur"`).
3. **Vérification des skills** : Toujours vérifier si un skill dédié existe avant de conclure à l'absence d'information.
4. **Message standard** : Si le wiki n'est pas indexé, retourner **exactement** le message :
   ```
   Aucun document n'a été indexé pour ce projet.
   Utilisez le bouton '+ Ajouter des documents' pour lancer l'ingestion.
   ```
5. **Citation des sources** : Si des informations sont trouvées, toujours citer la source (ex: `[JennyCompressorManual.pdf, p.XX]`).

## Pièges courants
- **Confondre absence d'information et information négative** : Si le wiki n'est pas indexé, ne pas inventer de réponse.
- **Négliger les requêtes élargies** : Toujours essayer plusieurs combinaisons de mots-clés avant de conclure.
- **Oublier de vérifier les skills** : Un skill mal nommé ou incomplet peut contenir l'information.
- **Ignorer le message standard** : Toujours retourner le message exact si le wiki n'est pas indexé.

## Exemple d'application
- **Question utilisateur** : "Quand faut-il faire la première vidange d'huile du compresseur ?"
- **Actions** :
  1. Recherche avec `"première vidange huile compresseur Jenny"` → Aucun résultat.
  2. Recherche avec `"vidange huile compresseur Jenny"` → Aucun résultat.
  3. Vérification du skill `maintenance-compresseur-jenny` → Non trouvé.
  4. Retour du message standard car le wiki n'est pas indexé.
