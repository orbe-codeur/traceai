# Wiki Schema — maintenance industrielle — compresseurs Jenny

## Domaine
maintenance industrielle — compresseurs Jenny

## Conventions
- Noms de fichiers : lowercase, tirets, sans espaces (ex: turbine-orc.md)
- Chaque page machine commence par un frontmatter YAML
- Utiliser `[[wikilinks]]` pour les références croisées (min 2 liens sortants)
- Toujours mettre à jour la date `updated` lors d'une modification
- Chaque nouvelle page doit être ajoutée à index.md
- Chaque action doit être ajoutée à log.md

## Frontmatter obligatoire
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

## Tags disponibles
- Équipements : turbine, pompe, compresseur, echangeur, moteur, variateur
- Constructeurs : enogia, grundfos, danfoss, abb, siemens, schneider
- Systèmes : orc, hydraulique, electrique, pneumatique, regulation
- Actions : maintenance-preventive, maintenance-corrective, inspection

## Seuils de création de page
- Créer une page quand une machine apparaît dans 2+ sources OU est centrale dans 1 source
- Ne PAS créer de page pour les mentions passagères
- Diviser une page quand elle dépasse ~200 lignes

## Politique de mise à jour
En cas de contradiction entre sources :
1. Vérifier les dates — les sources récentes prévalent généralement
2. Si contradiction réelle → noter les deux positions avec sources et dates
3. Marquer en frontmatter : `contradictions: [autre-machine]`
4. Signaler pour révision dans le rapport de lint
