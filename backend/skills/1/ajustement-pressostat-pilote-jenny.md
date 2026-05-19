---
name: ajustement-pressostat-pilote-jenny

description: "Use when ingérant/répondant/analysant des demandes d'ajustement de la pression de coupure du pressostat pilote ou principal sur un compresseur Jenny (modèles à piston)."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, pressostat, ajustement, Jenny, maintenance, pression-coupure]

---

## Quand utiliser
- **Demande explicite** : L'utilisateur demande comment **ajuster la pression de coupure** du pressostat pilote ou principal.
- **Contexte** : Le compresseur est un **Jenny Compressor** (modèle à piston).
- **Exemples de requêtes** :
  - "Comment ajuster la pression de coupure du pressostat pilote ?"
  - "Quelle est la procédure pour régler le pressostat sur un Jenny ?"
  - "Comment modifier la pression d'arrêt du compresseur Jenny ?"

---

## Étapes clés (basées sur JennyCompressorManual.pdf, p.26)
1. **Localiser le pressostat** :
   - Le pressostat est généralement situé sur le **manifold** ou près du **réservoir d'air**.
   - Il est équipé d'un **levier rotatif** pour le démarrage/arrêt manuel.

2. **Identifier les pressions de coupure** :
   - Le pressostat fonctionne avec **deux pressions prédéfinies** :
     - **Pression basse** : Le compresseur démarre quand la pression descend en dessous de cette valeur.
     - **Pression haute** : Le compresseur s'arrête quand la pression atteint cette valeur.

3. **Vérifier les valeurs actuelles** :
   - Utiliser le **manomètre du réservoir** pour lire la pression actuelle.
   - Comparer avec les **valeurs recommandées** (si disponibles dans le manuel ou la plaque signalétique).

4. **Ajustement (si procédure disponible)** :
   - **Tourner la vis de réglage** du pressostat (sens horaire pour augmenter la pression, sens anti-horaire pour diminuer).
   - **Utiliser un manomètre externe** pour valider les nouvelles valeurs.
   - **Ne pas dépasser la pression maximale** autorisée (vérifier dans le manuel).

5. **Tester le réglage** :
   - Redémarrer le compresseur et vérifier que les pressions de coupure correspondent aux valeurs souhaitées.

---

## Pièges courants
- **Dépassement de la pression maximale** : Risque de **surcharge** ou de **dommages** au compresseur. Toujours vérifier la **pression maximale autorisée** dans le manuel.
- **Absence de manomètre calibré** : Les réglages sans outil de mesure précis peuvent entraîner des **erreurs de calibration**.
- **Intervention sans coupure électrique** : **Danger électrique** — toujours couper l'alimentation avant toute manipulation.
- **Réglages incorrects** : Une pression de coupure trop basse peut entraîner un **démarrage intempestif**, et une pression trop haute peut causer une **surchauffe** ou une **usure prématurée**.

---

## Sources et références
- **JennyCompressorManual.pdf** (p.26) : Description des contrôles et indicateurs du compresseur Jenny.
- **Support Jenny** : [1-888-4-A-JENNY](tel:18884253669) pour obtenir des instructions précises ou des schémas.

---

## Limites
- **Procédure détaillée non indexée** : La procédure complète pour ajuster les pressions n'est pas encore extraite des documents. Se référer au manuel ou contacter le support.
- **Variantes de modèles** : Les modèles **Dual Control** et **Constant Run** peuvent avoir des **différences mineures** dans la localisation des composants.

---

## Workflow recommandé
1. **Rechercher dans le manuel** : Consulter les sections **"OPERATING CONTROLS AND INDICATORS"** et **"MAINTENANCE/ADJUSTMENTS"**.
2. **Vérifier la plaque signalétique** : Les pressions de coupure peuvent être indiquées directement sur le compresseur.
3. **Utiliser un manomètre externe** pour valider les réglages.
4. **Documenter les changements** : Noter les nouvelles valeurs de pression pour un suivi ultérieur.