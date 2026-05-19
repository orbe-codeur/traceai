---
name: recherche-documentation-ventilation-compresseur

description: "Use when ingérant/répondant/analysant des questions sur les dégagements de ventilation, les distances minimales ou les exigences de circulation d'air pour un compresseur Jenny ou similaire. Ce skill couvre les recherches dans le wiki, les manuels constructeur, et la mémoire pour extraire les valeurs de dégagement et les bonnes pratiques associées."

version: 1.0.0

author: TraceAI

metadata:
  hermes:
    tags: [ventilation, compresseur, dégagement, installation, Jenny, sécurité]

---

## Quand utiliser
- Répondre à une question sur le **dégagement de ventilation** requis autour d'un compresseur Jenny.
- Valider ou infirmer une distance de dégagement proposée par un technicien.
- Rechercher des **bonnes pratiques d'installation** liées à la ventilation des compresseurs.
- Compléter une fiche technique ou un rapport de maintenance avec les exigences de ventilation.


## Étapes systématiques
1. **Analyser la question** : Identifier si la question porte sur un dégagement spécifique (ex: 3 pieds) ou une procédure d'installation.
2. **Recherche dans le wiki** : Utiliser `search_wiki` avec des mots-clés comme `"dégagement ventilation compresseur Jenny"`, `"ventilation compresseur Jenny distance minimale"`, ou `"clearance Jenny compressor"`.
3. **Recherche dans les chunks (manuels)** : Utiliser `search_chunks` avec des requêtes similaires pour extraire les valeurs exactes depuis les manuels constructeur (ex: JennyCompressorManual.pdf).
4. **Vérification en mémoire** : Utiliser `search_memory` pour vérifier si des conventions locales ou des préférences client existent sur ce sujet.
5. **Synthèse des résultats** : Croiser les informations du wiki, des chunks et de la mémoire pour fournir une réponse **cohérente et sourcée**.
6. **Enregistrement dans la base de connaissances** : Si la question est récurrente, enregistrer la réponse dans la base de connaissances via `save_synthesis` pour une réutilisation future.


## Patterns spécifiques
- **Valeurs standard** : Pour les compresseurs Jenny, la valeur standard est **3 pieds (0,9 mètre)** de dégagement minimum autour de la machine. Cette valeur est souvent répétée dans le wiki et les manuels.
- **Justification technique** : Toujours associer la valeur de dégagement à la **prévention de la surchauffe** et à la **sécurité** (risque d'incendie, usure prématurée).
- **Sources prioritaires** : Privilégier les informations issues des **manuels constructeur** (JennyCompressorManual.pdf) et des pages wiki dédiées à la machine.
- **Pièges courants** :
  - Confondre le dégagement de ventilation avec d'autres distances (ex: dégagement électrique, accès pour maintenance).
  - Négliger de vérifier si des **conventions locales** ou des **exigences spécifiques au site** s'appliquent (ex: dégagement accru pour les compresseurs en atmosphère explosive).
  - Oublier de mentionner les **risques** liés à un dégagement insuffisant (surchauffe, incendie, non-conformité).


## Pièges courants
- **Dégagement vs. accès** : Ne pas confondre le dégagement de ventilation (3 pieds) avec les **accès pour maintenance** (qui peuvent nécessiter plus d'espace). Toujours vérifier les deux exigences.
- **Variantes de modèles** : Certains modèles de compresseurs Jenny peuvent avoir des exigences spécifiques. Toujours vérifier le modèle exact si possible.
- **Environnement d'installation** : En cas d'installation en espace confiné ou avec des contraintes particulières (ex: température ambiante élevée), le dégagement peut devoir être **augmenté**. Toujours consulter le manuel constructeur pour des cas spécifiques.
- **Normes locales** : Vérifier si des normes locales (ex: NFPA, OSHA) imposent des dégagements supplémentaires. Ces informations peuvent être dans la mémoire ou le wiki.


## Exemple d'application
**Question utilisateur** : *Quel dégagement de ventilation est requis autour du compresseur ?*

**Étapes suivies** :
1. Recherche dans le wiki avec `search_wiki("dégagement ventilation compresseur Jenny requirements")`.
2. Recherche dans les chunks avec `search_chunks("ventilation compresseur Jenny distance minimale")`.
3. Vérification en mémoire avec `search_memory("dégagement ventilation compresseur Jenny")`.
4. Synthèse des résultats : Le wiki et le manuel indiquent **3 pieds (0,9 m)** comme dégagement minimum.
5. Enregistrement de la réponse dans la base de connaissances via `save_synthesis`.

**Réponse finale** :
*Le dégagement de ventilation requis autour d'un compresseur Jenny est de **3 pieds (0,9 mètre) minimum** sur tous les côtés. Cette distance permet d'assurer une circulation d'air adéquate et d'éviter la surchauffe de la machine.*

**Sources** :
- [Jenny Compressor Wiki] : Spécifications techniques.
- [JennyCompressorManual.pdf, p.8 et p.22] : Exigences de ventilation et avertissements sur la surchauffe.