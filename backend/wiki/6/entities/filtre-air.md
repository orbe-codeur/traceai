---
title: "filtre-air"
type: entity
tags: [compresseur, maintenance, air-comprimé, filtration]
sources: [6.pdf, sources/jenny-compressor-operation-maintenance-manual.md]
---

# filtre-air

## Définition et contexte industriel

Le **filtre-air** (ou *intake filter* en anglais) est un composant essentiel des systèmes de production d'air comprimé, notamment dans les compresseurs industriels. Il est conçu pour purifier l'air aspiré avant qu'il ne soit comprimé, en éliminant les particules solides (poussières, débris, polluants atmosphériques) qui pourraient endommager les équipements en aval ou réduire leur efficacité.

Dans le contexte des compresseurs Jenny ou similaires, le filtre-air est généralement situé à l'entrée du système, juste avant le [[moteur-electrique]] ou [[moteur-essence]], et en amont du [[reservoir-air]]. Il joue un rôle critique dans la protection des composants internes du compresseur, comme les pistons, les soupapes et les joints, contre l'usure prématurée causée par des impuretés.

## Rôle et caractéristiques clés

### Fonctions principales
1. **Filtrage des particules** : Capture les impuretés présentes dans l'air ambiant (poussière, pollen, particules métalliques, etc.) pour éviter leur introduction dans le circuit d'air comprimé.
2. **Protection des équipements** : Préserve l'intégrité des composants internes du compresseur et des outils pneumatiques en aval.
3. **Amélioration de la qualité de l'air** : Contribue à réduire la contamination de l'air comprimé, ce qui est crucial pour les applications sensibles (ex. : industries pharmaceutiques, alimentaires, ou électroniques).
4. **Optimisation des performances** : Un filtre-air propre permet de maintenir un débit d'air optimal et de réduire la consommation d'énergie du compresseur.

### Caractéristiques techniques
- **Type de filtration** : Généralement de type *mécanique* (filtre à papier, mousse, ou filtre à cyclone) avec une capacité de rétention variable selon les modèles (ex. : 5 à 10 microns pour les filtres standards).
- **Matériaux** : Le média filtrant peut être en papier traité, en mousse polyuréthane, ou en fibres synthétiques résistantes à l'humidité.
- **Maintenance** : Le filtre-air doit être inspecté régulièrement et remplacé ou nettoyé selon les recommandations du fabricant (fréquence typique : toutes les 500 heures de fonctionnement ou selon l'environnement).
- **Indicateurs de colmatage** : Certains modèles incluent un indicateur de pression différentielle pour signaler quand le filtre doit être remplacé.

## Intégration dans le système

Le filtre-air est un maillon clé de la chaîne de production d'air comprimé. Il est généralement installé en **amont du compresseur**, juste après l'entrée d'air, et avant le [[reservoir-air]]. Son intégration correcte est essentielle pour éviter les fuites ou les courts-circuits d'air non filtré.

### Schéma typique de connexion
```
[Air ambiant] → [[filtre-air]] → [[moteur-electrique]]/[[moteur-essence]] → [[compresseur]] → [[reservoir-air]] → [[soupape-pilote]]/[[pressostat]] → Outils pneumatiques
```

### Interaction avec d'autres composants
- **[[reservoir-air]]** : Le filtre-air protège le réservoir en empêchant l'accumulation de contaminants qui pourraient corroder ses parois ou obstruer les [[soupapes]].
- **[[courroie-traction]]** : Bien que non directement lié, un filtre-air encrassé peut entraîner une surcharge du moteur, affectant indirectement la tension de la [[courroie-traction]].
- **[[pressostat]]** : Un filtre-air colmaté peut fausser les lectures de pression du [[pressostat]], entraînant des cycles de compression inefficaces.

## Maintenance et bonnes pratiques

### Tâches de maintenance préventive
| Fréquence       | Tâche                                                                 | Source                          |
|-----------------|-----------------------------------------------------------------------|---------------------------------|
| Quotidienne     | Vérifier visuellement l'état du filtre-air (pas de colmatage visible). | [6.pdf, p.28]                  |
| Hebdomadaire    | Nettoyer ou remplacer le filtre-air si nécessaire (selon l'environnement). | [sources/jenny-compressor-operation-maintenance-manual.md, p.26] |
| Mensuelle       | Inspecter le média filtrant pour détecter des signes d'usure ou de contamination excessive. | Bonnes pratiques industrielles |
| Selon besoin    | Remplacer le filtre-air en cas de chute de performance du compresseur ou d'augmentation de la consommation d'énergie. | [sources/jenny-compressor-operation-maintenance-manual.md, p.40] |

### Signes d'un filtre-air défectueux ou encrassé
- **Baisse de performance** : Le compresseur met plus de temps à atteindre la pression de consigne.
- **Augmentation de la consommation d'énergie** : Le moteur travaille plus pour compenser la restriction de débit.
- **Bruits anormaux** : Sifflements ou sifflements intermittents dus à une aspiration d'air perturbée.
- **Contamination visible** : Présence de poussière ou de débris sur le média filtrant lors de l'inspection.

### Procédures de remplacement
1. **Arrêter le compresseur** et couper l'alimentation électrique.
2. **Démonter le boîtier du filtre-air** en suivant les instructions du fabricant.
3. **Retirer le filtre usagé** et inspecter le boîtier pour détecter d'éventuels contaminants résiduels.
4. **Nettoyer le boîtier** si nécessaire (avec un chiffon sec ou de l'air comprimé).
5. **Installer un nouveau filtre** en s'assurant qu'il est correctement orienté (flèche de direction d'air visible).
6. **Remonter le boîtier** et vérifier l'étanchéité.
7. **Redémarrer le compresseur** et surveiller les performances.

## Sécurité et précautions
- **Ne jamais faire fonctionner le compresseur sans filtre-air** : Risque d'aspiration de particules abrasives ou de corps étrangers.
- **Utiliser des filtres adaptés** : Toujours remplacer le filtre par un modèle conforme aux spécifications du fabricant.
- **Éviter les fuites d'air** : Une fuite en aval du filtre peut entraîner une aspiration d'air non filtré.
- **Protéger le filtre des intempéries** : Dans les environnements extérieurs, utiliser un capot de protection pour éviter l'infiltration d'eau ou de neige.

## Références et normes
- **Normes de filtration** : Les filtres-air industriels sont souvent classés selon la norme **ISO 8573-1** (qualité de l'air comprimé) ou **EN 779** (filtres à air pour systèmes de ventilation).
- **Documentation Jenny** : Voir [sources/jenny-compressor-operation-maintenance-manual.md] pour les spécifications techniques détaillées.

## Voir aussi
- [[compresseur]]
- [[reservoir-air]]
- [[maintenance-preventive-orc]]
- [[procedure-demarrage-compresseur]]
- [[moteur-electrique]]
- [[moteur-essence]]
