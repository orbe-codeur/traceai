---
name: maintenance-purge-condensat-compresseur-jenny
description: "Use when ingérant/répondant/analysant des questions sur la fréquence de purge du condensat des réservoirs de compresseurs Jenny."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [maintenance, purge, condensat, compresseur, Jenny]
---

## Quand utiliser
- Pour toute question concernant la **fréquence** ou la **procédure** de purge du condensat sur un compresseur Jenny.
- Pour vérifier les bonnes pratiques de maintenance préventive sur les réservoirs.

## Patterns spécifiques
1. **Recherche initiale** : Toujours vérifier la page machine dans le **Machine Wiki** (ex: "Jenny Compressor") avant de répondre.
2. **Source prioritaire** : Privilégier le manuel constructeur (JennyCompressorManual.pdf) pour les valeurs exactes.
3. **Sécurité** : Rappeler systématiquement les risques (corrosion, explosion) liés à une purge négligée.

## Pièges courants
- **Confondre avec d'autres constructeurs** : Les fréquences varient selon les marques (ex: CompAir, Kaeser). Toujours vérifier l'étiquette constructeur.
- **Oublier la purge après chaque utilisation** : Même pour une utilisation courte, la purge est obligatoire.
- **Négliger les conditions environnementales** : En milieu humide ou poussiéreux, la fréquence peut être ajustée (à valider avec le manuel).

## Exemple d'application
```
Question : À quelle fréquence faut-il purger le condensat du réservoir ?
Action : Rechercher "purge condensat Jenny" dans le wiki → Trouver [JennyCompressorManual.pdf, p.10]
Réponse : Après chaque utilisation pour éviter les risques de corrosion et d'explosion.
```