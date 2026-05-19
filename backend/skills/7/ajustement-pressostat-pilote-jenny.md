---
name: ajustement-pressostat-pilote-jenny

description: "Use when adjusting the cut-out pressure and cut-in pressure of the pilot valve on a Jenny compressor. Includes safety steps and required tools."

version: 2.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, Jenny, soupape pilote, pressostat, réglage, pression de coupure, cut-out, cut-in]

---

## Quand utiliser
Ce skill s'applique pour :
- **Ajuster la pression de coupure** (*cut-out pressure*) : pression maximale à laquelle le compresseur s'arrête automatiquement.
- **Ajuster la pression de redémarrage** (*cut-in pressure*) : pression minimale à laquelle le compresseur redémarre.
- **Vérifier ou modifier le différentiel de pression** entre la coupure et le redémarrage.

**Contexte** : Maintenance préventive, diagnostic de surpression, ou adaptation aux besoins du réseau d'air comprimé.

---

## Outils nécessaires
- Clé à molette ou clé plate adaptée.
- **Manomètre de précision** (pour vérifier la pression avant/après réglage).
- Tournevis plat (si nécessaire pour retirer les caches).
- Équipements de protection individuelle (EPI) : gants, lunettes.

---

## Sécurité
⚠️ **IMPORTANT** : Respectez ces étapes pour éviter les accidents :
1. **Débrancher le compresseur** et **vider le réservoir** avant toute intervention.
2. **Porter des EPI** (gants, lunettes) pour éviter les projections d'huile ou de pression.
3. **Ne jamais desserrer les vis ou barillets de plus d'un tour** pour éviter une dépressurisation brutale.
4. La soupape pilote est en **laiton** : ne pas forcer pour éviter d'endommager les filets.

---

## Localisation de la soupape pilote
La soupape pilote est généralement située :
- **Sur le réservoir** du compresseur.
- **Près du pressostat** (si le compresseur en est équipé).

Elle comporte trois éléments principaux :
1. **Vis 'A'** : Réglage de la **pression de coupure** (*cut-out pressure*).
2. **Écrou de verrouillage 'B'** : Pour bloquer la vis 'A' après réglage.
3. **Barillet 'C'** : Réglage du **différentiel de pression** (écart entre coupure et redémarrage).

---

## Réglage de la pression de coupure (*cut-out pressure*)
### Étapes détaillées
1. **Préparation** :
   - Débranchez le compresseur et videz le réservoir.
   - Repérez la vis 'A' et l'écrou 'B' sur la soupape pilote.

2. **Desserrage de l'écrou de verrouillage** :
   - Utilisez une clé pour desserrer l'écrou 'B' (sans le retirer complètement).

3. **Réglage de la pression** :
   - **Tournez la vis 'A' dans le sens horaire** pour **augmenter** la pression de coupure.
   - **Tournez la vis 'A' dans le sens anti-horaire** pour **diminuer** la pression de coupure.
   - **Utilisez un manomètre** pour vérifier la pression pendant le réglage.

4. **Vérification** :
   - Une fois la pression souhaitée atteinte, **serrez l'écrou 'B'** pour bloquer la vis 'A'.
   - Redémarrez le compresseur et vérifiez que la coupure se produit à la pression souhaitée.

5. **Test final** :
   - Laissez le compresseur monter en pression et confirmez que l'arrêt automatique se fait à la bonne valeur.

---

## Réglage de la pression de redémarrage (*cut-in pressure*)
### Étapes détaillées
1. **Accès au barillet 'C'** :
   - Le barillet 'C' est généralement situé à côté de la vis 'A'.

2. **Réglage du différentiel** :
   - **Tournez le barillet 'C' dans le sens horaire** pour **augmenter le différentiel** (écart plus grand entre coupure et redémarrage).
   - **Tournez le barillet 'C' dans le sens anti-horaire** pour **diminuer le différentiel** (écart plus petit).

3. **Vérification** :
   - Après réglage, redémarrez le compresseur et vérifiez que le redémarrage se fait à la pression souhaitée.

---

## Valeurs par défaut et recommandations
⚠️ **ATTENTION** :
- **La pression de coupure par défaut n'est pas documentée dans les synthèses disponibles.**
- **Consultez le [JennyCompressorManual.pdf]** ou la **plaque signalétique** de votre compresseur pour obtenir la valeur recommandée.
- **Ne dépassez jamais la pression maximale admissible** indiquée sur le réservoir ou dans le manuel.

---

## Pièges courants
- **Confondre vis 'A' et barillet 'C'** : La vis 'A' règle la pression de coupure, le barillet 'C' règle le différentiel.
- **Oublier de revisser l'écrou 'B'** : Risque de désajustement accidentel.
- **Ne pas utiliser de manomètre** : Risque de réglage incorrect.
- **Ignorer les valeurs maximales** : Peut endommager le compresseur ou créer un risque de surpression.

---

## Documentation et suivi
- **Enregistrez le réglage** dans le rapport de maintenance.
- **Mettez à jour la mémoire du projet** avec la valeur de pression de coupure ajustée (si connue).