---
name: recherche-parametre-manquant-compresseur

description: "Use when ingérant ou répondant à des demandes de paramètres techniques manquants (pression, débit, température, etc.) dans les manuels de compresseurs industriels. Ce skill couvre les étapes de diagnostic, les sources à consulter, et les contacts d'urgence pour obtenir les données manquantes."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [compresseur, paramètre-manquant, diagnostic, maintenance, JennyCompressor]

---

## Quand utiliser
Ce skill est déclenché lorsque :
- Un utilisateur demande un **paramètre technique non documenté** dans les extraits de manuels indexés (ex : pression de coupure d'une soupape, pression maximale admissible, débit d'air, etc.).
- Une **valeur critique pour la sécurité ou la maintenance** est absente des documents accessibles.
- Il est nécessaire de **structurer une démarche de recherche** pour combler une lacune technique.

---

## Étapes clés du workflow

### 1. Identification du paramètre manquant
- **Exemple** : Pression de coupure de la soupape pilote, pression maximale du compresseur, couple de serrage d'un élément spécifique.
- **Vérifier** si le paramètre est mentionné dans les **spécifications techniques** ou les **procédures de sécurité** du manuel.

### 2. Recherche dans les documents indexés
- **Outils** :
  - `search_wiki` : Recherche par mots-clés dans le Machine Wiki.
  - `search_chunks` : Recherche sémantique dans les chunks indexés (ChromaDB) pour cibler le manuel concerné.
- **Cibles prioritaires** :
  - Sections **Spécifications techniques** (ex : p.8, p.16).
  - Sections **Sécurité** ou **Soupapes de sécurité** (ex : p.48).
  - **Index** du manuel pour localiser les pages pertinentes.

### 3. Vérification des sources externes
- **Consulter** :
  - Le **manuel complet** (si disponible en local ou via une source fiable).
  - Les **fiches techniques constructeur** ou les **bulletins de service**.
- **Contacter** :
  - Le **service après-vente du constructeur** (ex : Jenny Customer Service : 1-888-4-A-JENNY).
  - Préciser le **modèle exact** du compresseur pour obtenir une réponse précise.

### 4. Structuration de la réponse
- **Si le paramètre est trouvé** :
  - Citer la **source exacte** (fichier, page, section).
  - Exemple : `[JennyCompressorManual.pdf, p.48]` ou `[Machine Wiki, section Soupape pilote]`.
- **Si le paramètre n'est pas trouvé** :
  - **Ne pas inventer** de valeur.
  - **Recommander** de consulter le manuel complet ou le service après-vente.
  - **Mettre en garde** contre les risques de sécurité liés à l'absence de données.

### 5. Mise à jour de la base de connaissances
- **Créer un skill** pour documenter la démarche et éviter de répéter la recherche.
- **Exemple de skill** : `recherche-parametre-manquant-compresseur` (ce skill).

---

## Patterns spécifiques

### Pattern 1 : Paramètre absent des extraits indexés
- **Symptôme** : La recherche dans le wiki et les chunks ne retourne **aucun résultat** pour le paramètre demandé.
- **Action** :
  1. Vérifier si le paramètre est mentionné dans les **pages d'index** du manuel (ex : p.16 pour la nomenclature).
  2. Élargir la recherche avec des **synonymes** (ex : "soupape de sécurité" au lieu de "soupape pilote").
  3. Consulter les **sections de dépannage** (ex : p.48) pour des mentions indirectes.

### Pattern 2 : Paramètre mentionné mais non chiffré
- **Symptôme** : Le manuel mentionne l'existence d'un composant (ex : soupape pilote) mais **ne donne pas sa valeur de réglage**.
- **Action** :
  - **Ne pas extrapoler** : Risque de sécurité.
  - **Recommander** de contacter le constructeur avec le **numéro de modèle** et le **numéro de série**.

### Pattern 3 : Paramètre présent dans un autre document
- **Symptôme** : Le paramètre est trouvé dans un **document annexe** (ex : fiche technique, bulletin de service).
- **Action** :
  - **Indexer le document** dans le Machine Wiki si possible.
  - **Créer un lien** vers la source dans la réponse.

---

## Pièges courants

- **Inventer une valeur** : Toujours privilégier l'absence de données à une valeur non vérifiée. Risque : **sécurité compromise** (surcharge, explosion, etc.).
- **Négliger les sections de sécurité** : Les soupapes et paramètres critiques sont souvent dans des sections dédiées (ex : p.48 pour les soupapes de sécurité).
- **Oublier de préciser le modèle** : Toujours demander ou vérifier le **modèle exact** du compresseur pour éviter les erreurs de correspondance.
- **Ne pas citer la source** : Toujours indiquer **d'où provient l'information** (fichier, page, section) pour permettre une vérification ultérieure.

---

## Exemple d'application

### Cas : Pression de coupure de la soupape pilote (Jenny Compressor)
1. **Recherche** :
   - Mots-clés : `soupape pilote pression coupure Jenny`, `pressure relief valve setting Jenny`.
   - Résultats : Aucune valeur trouvée dans les extraits indexés.
2. **Vérification** :
   - Le manuel mentionne la soupape pilote (p.48) mais sans valeur de pression.
3. **Recommandation** :
   - Consulter le **manuel complet** ou contacter **Jenny Customer Service** (1-888-4-A-JENNY).
4. **Mise à jour** :
   - Créer ce skill pour documenter la démarche.

---

## Sources d'inspiration
- **Manuel JennyCompressorManual.pdf** : Sections p.8 (spécifications), p.16 (nomenclature), p.48 (soupapes et dépannage).
- **Retours utilisateurs** : Demandes récurrentes sur les paramètres manquants.
- **Bonnes pratiques** : Toujours privilégier la **traçabilité** et la **sécurité** dans les réponses techniques.