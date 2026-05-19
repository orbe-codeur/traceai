---
name: diagnostic-compresseur-pression

description: "Use when ingérant/répondant/analysant des diagnostics de compresseurs Jenny qui ne montent pas en pression. Ce skill encapsule les causes possibles, l'ordre de vérification recommandé, et les pièges courants pour éviter les erreurs de diagnostic."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, Jenny, pression, diagnostic, maintenance]

---

## Quand utiliser
Use this skill **uniquement** pour les compresseurs de la marque **Jenny** présentant le symptôme : **"le compresseur ne monte pas en pression"**. Il couvre les modèles industriels standards (ex: Jenny Ultimate Blue).

Utilise ce skill lorsque :
- Un technicien signale que le compresseur ne parvient pas à atteindre la pression de consigne.
- Une maintenance corrective ou préventive est planifiée sur un compresseur Jenny.
- Une procédure de dépannage standardisée est requise pour éviter les omissions.

**Do not use** for other compressor brands or different symptoms (e.g., overheating, abnormal noise).

---

## Patterns spécifiques

### 1. **Ordre de vérification recommandé**
Ce skill impose un ordre logique pour éviter les diagnostics erronés ou les réparations inutiles :

1. **Vérification des fuites** (priorité absolue) :
   - Fuites d'air aux raccords, réservoir, ou soupape de sécurité.
   - *Pattern* : Utiliser de l'eau savonneuse pour détecter les fuites. Si fuite détectée → réparer avant toute autre action.
   - *Source* : [JennyCompressorManual.pdf, p.54]

2. **Contrôle des éléments mécaniques** :
   - Filtre à air obstrué → nettoyer/remplacer.
   - Cylindre ou segments de piston usés → déglacer ou remplacer.
   - Clapet de refoulement défectueux → vérifier/remplacer.
   - *Pattern* : Toujours vérifier le filtre à air **avant** de démonter le cylindre.

3. **Éléments électriques et de commande** :
   - Pressostat défectueux ou mal réglé → ajuster ou remplacer.
   - Condensateur ou moteur défectueux → contacter le service client Jenny.
   - *Pattern* : Tester le pressostat **après** avoir vérifié les fuites et les éléments mécaniques.

4. **Environnement et lubrification** :
   - Température ambiante trop basse → déplacer ou utiliser une huile adaptée.
   - Niveau ou viscosité d'huile incorrect → compléter ou remplacer.
   - *Pattern* : Vérifier l'huile **uniquement** si les étapes précédentes sont conformes.

5. **Dimensionnement** :
   - Vérifier que le compresseur est adapté à l'application.
   - *Pattern* : Cette vérification est **la dernière étape** et ne doit pas être omise.


### 2. **Checklist de diagnostic**
Ce skill intègre une checklist réutilisable pour éviter les oublis :

```
✅ Vérifier les fuites d'air (raccords, réservoir, soupape de sécurité).
✅ Contrôler le filtre à air (nettoyage ou remplacement).
✅ Inspecter le cylindre et les segments de piston (usure).
✅ Tester le clapet de refoulement.
✅ Vérifier le pressostat (réglage ou remplacement).
✅ Contrôler le niveau et la qualité de l'huile.
✅ Tester le moteur et le condensateur (si nécessaire).
✅ Vérifier la température ambiante et l'environnement.
✅ Confirmer que le compresseur est dimensionné pour l'application.
```

---

## Pièges courants

- **⚠️ Négliger les fuites d'air** : Une fuite même minime peut empêcher la montée en pression. Toujours commencer par cette vérification.
  *Exemple* : Une fuite au niveau d'un raccord de 1/8" peut suffire à empêcher la pression de monter.

- **⚠️ Confondre usure du cylindre et problème de lubrification** : Une usure du cylindre nécessite une intervention mécanique, tandis qu'un problème de lubrification se résout par un changement d'huile. Ne pas inverser les étapes.

- **⚠️ Oublier de tester la soupape de sécurité** : Une soupape de sécurité défectueuse peut s'ouvrir prématurément et empêcher la montée en pression. Toujours la vérifier.

- **⚠️ Ignorer l'environnement** : Une température ambiante trop basse ou un environnement humide peut affecter les performances du compresseur. Toujours vérifier ces paramètres.

- **⚠️ Remplacer des pièces sans diagnostic complet** : Remplacer un pressostat ou un moteur sans avoir vérifié les fuites ou l'usure du cylindre peut entraîner des coûts inutiles.


---

## Exemple d'application

**Contexte** : Un technicien signale qu'un compresseur Jenny Ultimate Blue ne monte pas en pression après une maintenance.

**Application du skill** :
1. Le technicien suit l'ordre de vérification :
   - Il détecte une fuite au niveau d'un raccord (étape 1).
   - Il répare la fuite et relance le compresseur. La pression monte correctement.
2. Si aucune fuite n'est détectée, il passe à l'étape suivante (filtre à air, puis cylindre, etc.).

**Résultat** : Le diagnostic est complet, rapide, et évite des réparations inutiles.

---

## Sources et références
- [JennyCompressorManual.pdf, p.48, p.54]
- [wiki/syntheses/2026-05-19-comment-v-rifier-et-tester-la-soupape-de-s-curit-d-un-compre.md]
- [wiki/syntheses/2026-05-19-comment-ajuster-le-r-gulateur-de-pression-soupape-pilote-sur.md]
- [wiki/syntheses/2026-05-19-comment-v-rifier-le-niveau-d-huile-du-compresseur-jenny.md]