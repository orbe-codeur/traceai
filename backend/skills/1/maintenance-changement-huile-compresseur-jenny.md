---
name: maintenance-changement-huile-compresseur-jenny
description: "Use when ingérant/répondant/analysant des demandes de techniciens sur la vidange, le type d'huile, la fréquence ou les avertissements de sécurité pour les compresseurs Jenny (modèles à piston)."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [maintenance-preventive, lubrification, compresseur, jenny, huile]

---

## Quand utiliser
Ce skill est déclenché lorsque :
- Un technicien demande une **procédure détaillée** pour changer l'huile d'un compresseur Jenny.
- Une question porte sur le **type d'huile**, la **fréquence de vidange**, ou les **avertissements de sécurité** liés à la lubrification.
- Il faut **structurer une réponse** en combinant les informations du manuel JennyCompressorManual.pdf, la mémoire persistante, et les bonnes pratiques industrielles.
- L'utilisateur signale une **lacune documentaire** (ex : localisation des bouchons, quantité d'huile) et nécessite une **démarche de recherche** pour combler le manque.

---

## Informations clés à intégrer systématiquement

### 1. Avertissements de sécurité
- **Température** : Les pièces (aftercooler, pump head) sont **très chaudes** après utilisation. Laisser refroidir **30 minutes** avant toute intervention.
  *Source : [JennyCompressorManual.pdf, p.38]*
- **Lubrification** : Ne jamais faire fonctionner le compresseur **sans huile** ou avec un **niveau insuffisant**. Risque de défaillance mécanique et de perte de garantie.
  *Source : [JennyCompressorManual.pdf, p.38]*
- **Responsabilité** : Jenny décline toute responsabilité en cas de défaillance due à une lubrification inadéquate.
  *Source : [JennyCompressorManual.pdf, p.38]*

### 2. Type d'huile
- **Huile recommandée** : **Jenny Ultimate Blue Synthetic Oil** (viscosité non spécifiée dans les chunks indexés).
  *Source : [JennyCompressorManual.pdf, p.48]*
- **Alternative** : Si Jenny Ultimate Blue n'est pas disponible, utiliser une huile **synthétique** de viscosité équivalente (ex : SAE 30 ou ISO 68 pour compresseurs à piston). **Ne pas mélanger** différents types d'huile.

### 3. Fréquence de changement
| Fréquence       | Détails                                                                                     |
|-----------------|---------------------------------------------------------------------------------------------|
| **Première vidange** | Après **20 heures** de fonctionnement.                                                      |
| **Vidanges suivantes** | Tous les **200 heures** ou **annuellement** (selon l'usage, le plus restrictif).            |
| *Source : Mémoire persistante + [JennyCompressorManual.pdf, p.43]* |

### 4. Outillage requis
- Clé à molette ou clé adaptée (taille non spécifiée — à adapter au modèle du compresseur).
- Bac de récupération d'huile (capacité ≥ 1 litre).
- Entonnoir avec filtre.
- Chiffons propres.
- Gants et lunettes de protection (bonnes pratiques non documentées dans le manuel).

### 5. Procédure générique (à adapter)
*⚠️ **Informations manquantes** dans les chunks indexés : localisation des bouchons, quantité d'huile, méthode de vérification du niveau.*

#### Étapes :
1. **Préparation** :
   - Arrêter le compresseur et débrancher l'alimentation.
   - Laisser refroidir 30 minutes.
   - Placer un bac de récupération sous le carter.

2. **Vidange** :
   - Localiser le bouchon de vidange (sous le carter, hypothèse).
   - Dévisser avec une clé adaptée.
   - Laisser l'huile s'écouler complètement (5-10 minutes).
   - Nettoyer le bouchon et son joint avant de le revisser.

3. **Remplissage** :
   - Localiser le bouchon de remplissage (dessus ou côté du carter, hypothèse).
   - Verser l'huile neuve (Jenny Ultimate Blue Synthetic Oil) progressivement.
   - **Quantité non spécifiée** : Remplir jusqu'à ce que l'huile atteigne le bas du filetage du bouchon de remplissage (méthode par défaut pour les compresseurs à piston).
   - Vérifier le niveau (jauge ou bouchon de remplissage).

4. **Finalisation** :
   - Revisser le bouchon de remplissage.
   - Nettoyer les déversements.
   - Démarrer le compresseur et vérifier l'absence de fuites.
   - Recontrôler le niveau après 5 minutes de fonctionnement.

---

## Patterns spécifiques

### Pattern 1 : Demande de procédure détaillée
- **Symptôme** : L'utilisateur demande "Comment changer l'huile du compresseur Jenny ?".
- **Action** :
  1. Combiner les **avertissements de sécurité** (p.38), le **type d'huile** (p.48), et la **fréquence** (mémoire persistante).
  2. Fournir une **procédure générique** en signalant clairement les **lacunes documentaires** (localisation des bouchons, quantité d'huile).
  3. Recommander de consulter le **manuel complet** ou le **service après-vente Jenny** (1-888-4-A-JENNY).

### Pattern 2 : Question sur le type d'huile
- **Symptôme** : L'utilisateur demande "Quel type d'huile utiliser pour le compresseur Jenny ?".
- **Action** :
  1. Répondre : **Jenny Ultimate Blue Synthetic Oil** (p.48).
  2. Ajouter une **mise en garde** : Ne pas utiliser d'huile minérale ou de viscosité inadaptée.
  3. Si l'utilisateur insiste sur la viscosité, expliquer que cette information **n'est pas disponible** dans les chunks indexés et recommander de contacter le service après-vente.

### Pattern 3 : Lacune documentaire signalée par l'utilisateur
- **Symptôme** : L'utilisateur répond "Je n'ai pas trouvé cette info dans le manuel" ou "Où se trouve le bouchon ?".
- **Action** :
  1. **Reconnaître la lacune** et remercier l'utilisateur pour le signalement.
  2. **Structurer une réponse** qui combine :
     - Les informations disponibles (sécurité, fréquence, type d'huile).
     - Une **procédure générique** basée sur les bonnes pratiques.
     - Une **recommandation claire** pour obtenir les détails manquants (manuel complet ou service après-vente).
  3. **Créer un skill** pour documenter cette approche et éviter de répéter la recherche.

### Pattern 4 : Demande de fréquence de vidange
- **Symptôme** : L'utilisateur demande "À quelle fréquence changer l'huile du compresseur Jenny ?".
- **Action** :
  1. Répondre avec le tableau de fréquence (20h, 200h, annuel).
  2. Préciser que la **fréquence annuelle** s'applique si elle est plus restrictive que 200 heures.
  3. Citer la source : mémoire persistante + [JennyCompressorManual.pdf, p.43].

---

## Pièges courants

1. **Inventer des détails** :
   - ❌ **Ne pas inventer** la localisation des bouchons, la quantité d'huile, ou la méthode de vérification du niveau.
   - ✅ **Signaler les lacunes** et recommander de consulter le manuel complet ou le service après-vente.

2. **Oublier les avertissements de sécurité** :
   - Toujours inclure les **risques de température** et de **lubrification inadéquate** pour éviter les accidents ou les défaillances.

3. **Négliger la fréquence** :
   - Toujours préciser que la **première vidange** est à 20 heures, puis **200 heures ou annuel** (le plus restrictif).

4. **Mauvaise interprétation des chunks** :
   - Les chunks indexés ne couvrent pas la procédure détaillée. **Ne pas se fier uniquement aux chunks** pour répondre à une demande de procédure.

5. **Ne pas citer les sources** :
   - Toujours indiquer **d'où provient l'information** (ex : [JennyCompressorManual.pdf, p.38]) pour permettre une vérification ultérieure.

6. **Ignorer les bonnes pratiques** :
   - Même si le manuel ne le mentionne pas, inclure des **conseils de sécurité** (gants, lunettes, nettoyage des déversements) pour une réponse complète.

---

## Exemple d'application

### Cas 1 : Technicien demande une procédure complète
**Entrée utilisateur** : "Comment changer l'huile du compresseur Jenny ?"
**Action** :
1. Combiner les avertissements (p.38), le type d'huile (p.48), et la fréquence (mémoire persistante).
2. Fournir une procédure générique en signalant les lacunes.
3. Recommander de contacter le service après-vente pour les détails manquants.

**Sortie** :
```markdown
### Procédure pour changer l'huile du compresseur Jenny
*Source : [JennyCompressorManual.pdf, p.38 et p.48] + Mémoire persistante*

#### Avertissements de sécurité
- Température : Laisser refroidir 30 minutes avant toute intervention.
- Lubrification : Ne jamais faire fonctionner sans huile.

#### Type d'huile
- Jenny Ultimate Blue Synthetic Oil (viscosité non spécifiée).

#### Fréquence
- Première vidange : 20 heures.
- Vidanges suivantes : 200 heures ou annuel.

#### Procédure générique
1. Préparation : Arrêter, refroidir, placer un bac de récupération.
2. Vidange : Localiser le bouchon (sous le carter), dévisser, laisser s'écouler.
3. Remplissage : Localiser le bouchon (dessus/côté), verser l'huile progressivement.
4. Finalisation : Revisser, nettoyer, vérifier les fuites.

⚠️ **Lacunes** : Localisation exacte des bouchons et quantité d'huile non documentées. Consulter le manuel complet ou le service après-vente (1-888-4-A-JENNY).
```

### Cas 2 : Technicien signale une lacune
**Entrée utilisateur** : "Je n'ai pas trouvé où se trouve le bouchon de vidange dans le manuel."
**Action** :
1. Reconnaître la lacune.
2. Fournir une procédure générique en signalant l'hypothèse (sous le carter).
3. Recommander de consulter le manuel complet ou le service après-vente.

**Sortie** :
```markdown
⚠️ **Lacune signalée** : La localisation exacte du bouchon de vidange n'est pas documentée dans les chunks indexés.

**Hypothèse** : Situé sous le carter (procédure générique pour les compresseurs à piston).

**Recommandation** : Consulter le manuel complet JennyCompressorManual.pdf ou contacter le service après-vente Jenny au 1-888-4-A-JENNY en précisant le modèle et le numéro de série.
```

---

## Sources d'inspiration
- **Manuel JennyCompressorManual.pdf** : Pages 38 (avertissements), 48 (type d'huile), et 43 (fréquence).
- **Mémoire persistante** : Fréquences de maintenance pour le compresseur Jenny.
- **Bonnes pratiques industrielles** : Procédures génériques pour les compresseurs à piston (vidange à chaud, nettoyage des bouchons, vérification des fuites).
- **Retours utilisateurs** : Demandes récurrentes sur les lacunes documentaires (localisation des bouchons, quantité d'huile).