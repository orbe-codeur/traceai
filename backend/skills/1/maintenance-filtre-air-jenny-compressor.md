---
name: maintenance-filtre-air-jenny-compressor

description: "Use when ingérant/répondant/analysant des procédures de maintenance liées au nettoyage ou au remplacement du filtre à air des compresseurs Jenny Compressor (modèles à piston)."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [maintenance, filtre-air, compresseur, Jenny, préventif]

---

## Quand utiliser
Ce skill s'applique **uniquement** pour les compresseurs d'air à piston de la marque **Jenny Compressor**.

Utilisez-le lorsque :
- Un technicien demande la procédure de **nettoyage ou remplacement du filtre à air**.
- Une **inspection visuelle** révèle un filtre encrassé ou endommagé.
- La **checklist de préparation** (Section 5 du manuel) nécessite une vérification du filtre à air.
- L'environnement de travail est **poussiéreux** (ex : chantier, atelier avec particules fines).

**Exclusions** : Ne pas utiliser pour d'autres marques ou types de compresseurs (ex : compresseurs à vis, MO206).

---

## Fréquences recommandées
| Action               | Fréquence       | Condition particulière                     | Source                     |
|----------------------|-----------------|--------------------------------------------|----------------------------|
| **Vérification**     | **Quotidienne** | Avant chaque utilisation                   | [JennyCompressorManual.pdf, Section 5] |
| **Nettoyage**        | **Mensuelle**   | Environnement standard                     | [JennyCompressorManual.pdf, p.43] |
| **Nettoyage**        | **Tous les 15 jours** | Environnement très poussiéreux (ex : chantier) | [JennyCompressorManual.pdf, p.43] |
| **Remplacement**      | **Selon usure** | Filtre fissuré, déformé ou inefficace      | [JennyCompressorManual.pdf, Section 5] |

---

## Procédure de nettoyage (étapes détaillées)
1. **Arrêt et sécurité** :
   - Éteignez le compresseur et débranchez-le.
   - Attendez que le moteur refroidisse (risque de brûlure).

2. **Accès au filtre** :
   - Localisez le **boîtier du filtre à air** (généralement près du moteur ou du carter).
   - Dévissez ou déclipsez le couvercle du boîtier.

3. **Retrait du filtre** :
   - Sortez délicatement le filtre à air.
   - **Inspectez visuellement** : rejetez-le s'il est fissuré, déformé ou saturé d'huile.

4. **Nettoyage** :
   - **Méthode 1 (air comprimé)** :
     - Utilisez un **compresseur d'air propre** (pression < 30 psi) pour souffler les poussières **de l'intérieur vers l'extérieur** du filtre.
     - Maintenez le filtre à une distance de 10-15 cm pour éviter de l'endommager.
   - **Méthode 2 (chiffon sec)** :
     - Passez un **chiffon microfibre sec** sur la surface extérieure.
     - **Ne jamais utiliser d'eau, de solvants ou d'huile** (risque de colmatage ou de détérioration du matériau filtrant).

5. **Réinstallation** :
   - Replacez le filtre dans le boîtier **dans le bon sens** (flèche de direction d'air visible).
   - Fermez le couvercle et serrez les fixations.

6. **Test** :
   - Redémarrez le compresseur et vérifiez l'absence de **baisse de performance** ou de **bruit anormal**.

---

## Procédure de remplacement
1. **Identification du filtre compatible** :
   - Consultez le **manuel Jenny Compressor** (Section 5) ou le **numéro de pièce** indiqué sur l'ancien filtre.
   - Utilisez uniquement des **filtres certifiés Jenny** pour éviter les problèmes de performance ou de garantie.

2. **Retrait de l'ancien filtre** :
   - Suivez les étapes 1 à 3 de la procédure de nettoyage.

3. **Installation du nouveau filtre** :
   - Placez le nouveau filtre dans le boîtier **en respectant le sens de l'air** (flèche visible).
   - Fermez le couvercle et serrez les fixations.

4. **Vérification** :
   - Redémarrez le compresseur et contrôlez :
     - L'absence de **fuites d'air** autour du boîtier.
     - Une **pression stable** dans le réservoir.

---

## Pièges courants
1. **Nettoyage incorrect** :
   - **Erreur** : Utiliser de l'eau ou des solvants pour nettoyer le filtre.
   - **Conséquence** : Détérioration du matériau filtrant, colmatage accéléré.
   - **Solution** : Toujours utiliser de l'air comprimé ou un chiffon sec.

2. **Réinstallation à l'envers** :
   - **Erreur** : Placer le filtre dans le mauvais sens (flèche de direction d'air ignorée).
   - **Conséquence** : Réduction de l'efficacité de filtration, entrée de poussières dans le moteur.
   - **Solution** : Vérifier la flèche de direction **avant** de refermer le boîtier.

3. **Filtre non compatible** :
   - **Erreur** : Utiliser un filtre générique ou non certifié.
   - **Conséquence** : Risque de **surchauffe**, **baisse de performance**, ou **endommagement du compresseur**.
   - **Solution** : Toujours vérifier la référence du filtre dans le manuel ou auprès du support Jenny.

4. **Oubli de la vérification quotidienne** :
   - **Erreur** : Ne pas inspecter le filtre avant chaque utilisation.
   - **Conséquence** : Risque de **surchauffe**, **usure prématurée du moteur**, ou **panne**. 
   - **Solution** : Intégrer la vérification du filtre dans la **checklist quotidienne** (Section 5).

5. **Environnement sous-estimé** :
   - **Erreur** : Ne pas adapter la fréquence de nettoyage à l'environnement (ex : chantier poussiéreux).
   - **Conséquence** : Colmatage rapide du filtre, **réduction du débit d'air**.
   - **Solution** : Augmenter la fréquence de nettoyage (ex : tous les 15 jours) en cas d'exposition à des particules fines.

---

## Outils et matériaux nécessaires
| Élément               | Spécifications                          | Remarques                                  |
|-----------------------|-----------------------------------------|--------------------------------------------|
| **Filtre à air**      | Référence Jenny Compressor (Section 5)  | À remplacer si endommagé ou inefficace.   |
| **Air comprimé**      | Pression < 30 psi                       | Utilisé pour le nettoyage.                |
| **Chiffon microfibre**| Sec et propre                           | Alternative au nettoyage à l'air comprimé.|
| **Tournevis**         | Taille adaptée au boîtier              | Pour ouvrir/démonter le couvercle.        |

---

## Références croisées
- **Maintenance quotidienne** : Vérification du niveau d'huile, vidange des condensats. *Source : [JennyCompressorManual.pdf, p.43]*
- **Ventilation requise** : 3 pieds (0,9 m) de dégagement. *Source : [JennyCompressorManual.pdf, p.8]*
- **Température max** : > 240°F (115°C). *Source : [JennyCompressorManual.pdf, p.8]*

---

## Notes complémentaires
- **Documentation** : La procédure détaillée est disponible dans la **Section 5** du **JennyCompressorManual.pdf**. En cas de doute, contacter le support Jenny : [1-888-4-A-JENNY](tel:18884253669).
- **Formation** : Former les techniciens à reconnaître les signes d'un filtre inefficace (baisse de performance, bruit anormal).
- **Amélioration continue** : Mettre à jour ce skill si de nouvelles références de filtres ou des procédures modifiées sont publiées par Jenny.