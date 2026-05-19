---
name: recherche-couple-serrage-compresseur-jenny
description: "Use when ingérant/répondant/analysant des questions techniques sur des couples de serrage (boulons de culasse, brides, etc.) ou des procédures de serrage pour des compresseurs Jenny ou similaires."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [couple-serrage, compresseur, Jenny, maintenance, manuel-constructeur]
---

## Quand utiliser
- Pour répondre à des questions techniques sur des couples de serrage ou des procédures de serrage pour des compresseurs Jenny.
- Pour guider la recherche dans des manuels PDF ou des bases de connaissances techniques.
- Pour éviter de répéter des recherches inefficaces ou des patterns de recherche incorrects.

## Patterns spécifiques
1. **Mots-clés initiaux** : Commencer par des termes **spécifiques** combinant la machine, la pièce et l'action (ex: `"couple serrage boulons culasse compresseur Jenny"`).
2. **Élargissement des recherches** : Si aucun résultat, élargir avec des termes **génériques** comme `torque`, `serrage`, `boulons`, `culasse`, `cylinder head bolts`, `torque values`, etc.
3. **Vérification des chunks** : Toujours rechercher dans les **chunks** (manuels PDF indexés) pour des tableaux de couples ou des procédures de maintenance. Les manuels constructeurs contiennent souvent des valeurs techniques dans des tableaux ou des sections dédiées.
4. **Consultation de la mémoire** : Vérifier si une réponse ou une référence constructeur existe déjà en mémoire.
5. **Gestion des absences d'information** : Si aucune source ne contient l'information, **informer clairement** l'utilisateur que le wiki n'est pas indexé pour cette information et suggérer d'ajouter les documents manquants (ex: manuel de réparation, fiche technique).

## Pièges courants
- **Rester sur des mots-clés trop spécifiques** : Ne pas élargir suffisamment les recherches (ex: ne pas essayer `torque values` ou `cylinder head bolts`).
- **Oublier les chunks** : Les manuels PDF (chunks) contiennent souvent des tableaux de couples ou des procédures techniques absentes du wiki.
- **Supposer que l'information est toujours disponible** : Certains constructeurs (comme Jenny) ne fournissent pas ces détails dans les manuels grand public ou en ligne. Il faut parfois obtenir ces informations via des canaux dédiés (ex: service technique du constructeur).
- **Ne pas informer clairement l'utilisateur** : Toujours expliquer que l'information n'est pas disponible dans les sources indexées et proposer une solution (ex: ajouter des documents).

---
**Exemple d'utilisation** :
- Question utilisateur : `"Quel est le couple de serrage des boulons de culasse du compresseur Jenny ?"`
- Action : Appliquer le pattern ci-dessus pour rechercher dans le wiki, les chunks, et la mémoire. Si rien n'est trouvé, informer l'utilisateur et suggérer d'ajouter les documents pertinents.