---
name: precautions-electriques-installation-compresseur-jenny
description: "Use when ingérant/répondant/analysant des documents techniques ou procédures liés aux précautions électriques pour l'installation ou la maintenance d'un compresseur Jenny (marque générique ou constructeur Jenny)."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [electrique, installation, compresseur, Jenny, mise-à-la-terre, disjoncteur, fusible, NEC]

---

## Quand utiliser
Ce skill doit être utilisé **à chaque fois** qu'un technicien ou un ingénieur doit :
- Installer un compresseur Jenny sur un nouveau site.
- Vérifier la conformité électrique d'une installation existante.
- Diagnostiquer un problème lié à l'alimentation électrique (surchauffe, disjoncteur qui saute, choc électrique).
- Former du personnel sur les bonnes pratiques électriques pour les compresseurs Jenny.


## Checklist d'installation électrique (à cocher systématiquement)

### 1. Alimentation électrique
- [ ] Vérifier que la **tension d'alimentation** (ex : 115V, 230V) correspond aux **spécifications du compresseur** (étiquette moteur ou manuel).
- [ ] Vérifier que l'**ampérage du circuit** est suffisant pour le compresseur (voir plaque signalétique du moteur).
- [ ] Utiliser un **circuit dédié** : ne pas partager le circuit avec d'autres équipements.
- [ ] Vérifier que le **disjoncteur** est adapté à la puissance du compresseur (calibre en ampères).

### 2. Fusibles
- [ ] Utiliser des **fusibles à retard** (marqués "D") si le circuit est protégé par des fusibles.
- [ ] Ne jamais remplacer un fusible par un modèle de **calibre supérieur** sans vérifier la section des câbles (risque d'incendie).
- [ ] Vérifier que les fusibles sont **intacts** et adaptés à la charge.

### 3. Mise à la terre (Grounding)
- [ ] Vérifier que le compresseur est **correctement mis à la terre** (fil vert ou vert/jaune).
- [ ] Vérifier que la **prise murale** est conforme aux normes locales (ex : NEC aux États-Unis) et **correctement mise à la terre**.
- [ ] **Ne jamais modifier** la fiche du câble d'alimentation.
- [ ] Utiliser **uniquement des rallonges 3 fils avec prise de terre** (3 broches) si nécessaire.

### 4. Câblage
- [ ] Vérifier que la **section des câbles** est adaptée à la distance entre le compresseur et la source d'alimentation (ex : +1 section pour 25-50 pieds).
- [ ] Utiliser des câbles **résistants à 110°C**.
- [ ] Vérifier que **toutes les connexions électriques sont serrées** (risque de surchauffe ou d'arc électrique).
- [ ] Garder les connexions **au sec** et **hors du sol**.

### 5. Conformité et sécurité
- [ ] Respecter les **normes locales et nationales** (ex : NEC Article 422-4 aux États-Unis, ou équivalent local).
- [ ] En cas de doute, faire appel à un **électricien qualifié** pour valider l'installation.
- [ ] **Ne jamais travailler** sur les connexions électriques sans avoir **débranché le compresseur** et vérifié l'absence de tension.


## Pièges courants
- ❌ **Câble inadapté** : Utiliser un câble de section trop faible → surchauffe du moteur ou incendie.
- ❌ **Circuit partagé** : Brancher le compresseur sur un circuit déjà utilisé par d'autres équipements → disjoncteur qui saute.
- ❌ **Mise à la terre absente ou défectueuse** : Risque mortel de choc électrique.
- ❌ **Fusible inadapté** : Remplacer un fusible 15A par un 20A sans vérifier les câbles → risque d'incendie.
- ❌ **Modification du câble** : Couper ou modifier la fiche du compresseur → annulation de la garantie et risque électrique.


## Exemple de workflow
1. **Lire la plaque signalétique** du compresseur pour identifier la tension et l'ampérage requis.
2. **Vérifier le circuit électrique** : tension, ampérage, disjoncteur, fusibles.
3. **Contrôler la mise à la terre** : fil de terre présent, prise murale conforme.
4. **Vérifier les câbles** : section adaptée, connexions serrées, pas de traces de surchauffe.
5. **Tester l'installation** : démarrer le compresseur et surveiller les anomalies (bruit, odeur de brûlé, disjoncteur qui saute).
6. **Documenter** : Remplir un rapport d'installation avec les valeurs mesurées et les vérifications effectuées.


## Sources fiables
- **JennyCompressorManual.pdf** (pages 5, 22, 32) : Instructions officielles du constructeur.
- **NEC Article 422-4** (États-Unis) ou équivalent local : Normes électriques à respecter.

---
*Ce skill est conçu pour être utilisé en complément des manuels constructeur et des normes locales. Toujours prioriser les documents officiels du fabricant.*