# TraceAI — État des Lieux Critique
> Rédigé le 2026-05-18. Mis à jour le 2026-05-18. Document interne. Brutal et honnête.

---

## 1. La vraie vision (clarifiée)

Ce n'est pas un outil pour développeurs. C'est un outil pour un **collègue non-technicien dans une entreprise industrielle**.

Le scénario cible :

```
Collègue arrive le matin
    ↓
Glisse 80 PDFs dans TraceAI (interface web)
    ↓
Agent : "J'ai trouvé 3 machines. Ce dossier concerne quel site ?"
Collègue répond en 2 clics
    ↓
Agent travaille seul — 20 minutes
    ↓
Collègue : "Quel est le planning maintenance du compresseur 3 ?"
Agent : "Voici — purge quotidienne [p.28], courroie 50h [p.40] ✅ vérifié"
```

**Zéro développeur présent. Zéro curl. Zéro expertise technique requise.**

L'autonomie de l'agent n'est pas une fin en soi — elle sert à rendre le produit utilisable par quelqu'un qui n'est pas nous.

### Ce que ça veut dire concrètement

- L'ingestion doit fonctionner **sans supervision** sur des documents hétérogènes
- L'interface doit être **accessible à un non-technicien**
- Les réponses doivent signaler **quand faire confiance et quand vérifier**
- Le système doit **apprendre et s'améliorer** entre les sessions sans intervention
- Ça doit tourner **en local** pour les clients qui ne veulent pas envoyer leurs données au cloud

### Ce que ça ne veut PAS dire

TraceAI n'est **pas** un système de décision autonome. Il ne remplace pas le jugement du technicien. C'est un **outil de découverte et d'accès à l'information** — comme un GPS, pas comme un pilote automatique.

Un GPS se trompe parfois. Les gens l'utilisent quand même parce qu'il est 10× plus utile que la carte papier. Pour la maintenance : trouver une info en 10 secondes au lieu de chercher 2 heures dans 300 PDFs — même avec 5% d'erreurs, c'est un gain immense.

**Le positionnement juste :** outil de découverte et d'accès → le technicien vérifie quand c'est critique.

---

## 2. Ce qu'on a réellement

### Ce qui fonctionne (testé, validé)

**Phase 1 — Checklist PDF** ✅
- Extraction 3 passes (TOC → chunks → merge) sur manuels 50-120 pages
- Traçabilité complète (qui, quand, note, témoin)
- Export PV HTML
- Validé sur Jenny Compressor 54 pages → 126 étapes
- **C'est le seul feature qui a vu un vrai document**

**Agent core Hermes** ✅
- Boucle tool calling, 15 itérations max
- Mémoire persistante SQLite FTS5
- Skills auto-générés post-tour (background review)
- Continuité cross-session
- Streaming SSE
- Cron engine (alertes planifiées)
- Orchestrateur multi-agents (delegate_task)

**Wiki LLM** ✅ (fonctionne sur 1 document)
- `ingest_document_llm()` → one-call Mistral-large
- `health_check()`, `lint_wiki()`, `heal_missing_entities()`
- Knowledge graph Pass1 (regex) + Pass2 (LLM), vis.js

### Ce qui existe mais est cassé ou inutilisable

**ChromaDB** ❌
Présent dans le code. Jamais alimenté par les pages wiki Phase B.
`search_chunks` appelle ChromaDB mais les documents ingérés via `ingest_document_llm()` ne sont **jamais embeddés**. La recherche sémantique est aveugle sur 100% du contenu Phase B.

**Wiki structuré** ❌
Les pages générées sont du **LLM prose**. Pas de tableaux typés, pas de champs vérifiables, pas de merge logique. Si tu ingères un 2ème document qui contredit le premier, la page est réécrite — la contradiction est perdue.

**Frontend Phase B** ❌
Tout ce qu'on a construit (wiki-ingest, orchestrateur, streaming, cron, graph) est accessible **uniquement en curl**. Le collègue non-technicien ne peut rien faire sans le développeur.

**Multi-document** ❌
Testé uniquement sur **1 document** (Jenny Compressor Manual). On ignore si 10 documents sur la même machine produisent un wiki cohérent ou une soupe contradictoire.

**Anti-hallucination** ❌
Aucune vérification post-génération. Les valeurs numériques (couples, pressions, fréquences) ne sont pas cross-checkées. Pour un technicien qui suit une instruction fausse sur une installation critique — risque réel.

---

## 3. Pourquoi c'est pas bien

### 3.1 Le problème fondamental : l'autonomie sans accessibilité est inutile

L'agent est autonome. Mais seul un développeur avec curl peut s'en servir.

```
Ce qu'on a :                  Ce qu'il faut :
Agent autonome Hermes-grade   Agent autonome ACCESSIBLE
        ✅                             ❌
```

L'autonomie technique sans interface utilisable = zéro valeur pour le collègue.

### 3.2 Couche data cassée, architecture belle

On a bâti une architecture d'agents sophistiquée sur une **couche data qui ne tient pas**.

- Wiki en LLM prose → données non fiables
- ChromaDB vide → recherche sémantique aveugle
- Graph avec 17 nœuds sur 1 document → expansion quasi nulle
- Zéro vérification des claims numériques

On optimise la logistique avant d'avoir la marchandise.

### 3.3 Diversité documentaire sous-estimée

Dans une vraie usine : PDFs scannés à 200 DPI avec café dessus, docs Word 2003, Excel de pièces avec 47 colonnes, manuels en allemand + français, annotations manuscrites. Le parser actuel gère les PDFs numériques propres. Le reste est du travail non adressé.

### 3.4 La résolution de contradictions nécessite un humain

L'agent détecte que le manuel 2019 dit 6 ft-lb et le rapport 2022 dit 8 ft-lb. Mais décider lequel est juste — ça nécessite quelqu'un avec la connaissance machine. Le collègue qui a déposé les docs sait-il répondre ? Souvent non. Ce n'est pas un problème technique, c'est un problème organisationnel que le produit doit anticiper.

### 3.5 Zéro validation terrain

**On n'a jamais mis le produit devant un vrai technicien.** Phase 1 est validée techniquement, pas métier. On construit Phase B, Phase B+, orchestrateur multi-agents sur des hypothèses non validées sur Phase 1.

### 3.6 Dispersion technique

En une session on a implementé context compressor, background review, curator, orchestrateur, cron, streaming. **Aucun de ces 6 features ne rend l'outil accessible au collègue ni ne fiabilise les réponses.**

### 3.7 On-premise non adressé

Les clients industriels visés ne vont **pas** envoyer leurs données à Mistral cloud. Plans de maintenance, données de pannes, schémas machines — c'est confidentiel. Zéro stratégie on-premise = deal breaker sur 60-70% du marché cible.

---

## 4. Est-ce un fantasme ?

**Non. Mais avec des nuances importantes.**

### Ce qui est faisable maintenant
20-30 PDFs bien formés (manuels constructeurs numériques propres), agent qui pose 3-4 questions, ingère, répond avec citations. Sur documents de bonne qualité dans un périmètre clair — ça marche. Validé sur Jenny Compressor.

### Ce qui est faisable dans 2-3 mois
100 documents hétérogènes. Wiki structuré. Réponses avec score de confiance. Interface accessible à un non-technicien. Ingestion nocturne automatique. C'est le produit réaliste à horizon proche.

### Ce qui sera toujours limité
L'autonomie complète ("sans que tu sois jamais là") a des limites. Les cas limites (format inconnu, doc corrompu, question hors corpus, contradiction critique) nécessiteront toujours une intervention humaine. Avec un bon système : 5% des cas. Acceptable, mais le 5% existera toujours.

### Le niveau de fiabilité correct à promettre
| Usage | Fiabilité visée | Faisable ? |
|---|---|---|
| Trouver une info (planning, spec, procédure) | GPS — 95% | ✅ Oui |
| Prendre une décision technique sans vérifier | Aéronautique — 99.9% | ❌ Pas avec LLMs actuels |

**Promettre le GPS, pas le pilote automatique.**

---

## 5. Les agents — état honnête

### Agents existants

| Agent | Rôle | Valeur pour le collègue |
|---|---|---|
| `TraceAIAgent` | Boucle principale | ✅ Cœur du produit |
| `TraceAIOrchestratorAgent` | Délègue en parallèle | ⚠️ Utile pour ingestion batch. Sous-utilisé. |
| `BackgroundReview` | Update skills/mémoire post-tour | ⚠️ Valeur à long terme. Invisible pour l'utilisateur. |
| `Curator` | Maintenance skills | ⚠️ Overkill pour l'état actuel. |
| `CronScheduler` | Jobs planifiés (alertes nocturnes) | ✅ Valeur réelle. |

### Agents manquants (prioritaires)

| Agent | Valeur collègue | Prérequis |
|---|---|---|
| `IngestionPlannerAgent` | ⭐⭐⭐ Élevée — c'est le flux principal | Peut être construit maintenant |
| `WikiRAGAgent` | ⭐⭐⭐ Élevée si wiki structuré | Wiki structuré d'abord |
| `ChunkRAGAgent` | ⭐⭐⭐ Élevée si ChromaDB alimenté | ChromaDB d'abord |
| `HermesBrain` (routing) | ⭐⭐ Moyenne — optimisation | WikiRAG + ChunkRAG d'abord |
| `GraphRAGAgent` | ⭐ Faible avant 50+ docs | Graph dense d'abord |
| `CrossDocRAGAgent` | ⭐⭐⭐ Élevée à 100+ docs | ChromaDB + multi-docs d'abord |

---

## 6. Probabilité de réussir

**Oui, avec les bons choix.**

| Chemin | Probabilité |
|---|---|
| Continuer l'infrastructure agent (chemin actuel) | 30% |
| Frontend accessible + data layer + validation terrain | 70% |

**Ce qui joue en notre faveur :**
- Problème réel, mal adressé par les GMAO existants
- Architecture Hermes solide — vraie fondation
- Phase 1 vendable maintenant pour financer la suite
- Le marché PME industrielle n'est pas encore adressé par des acteurs AI sérieux

**Ce qui nous met en danger :**
- Continuer à construire de l'infra sophistiquée sur des données non fiables
- Pas d'on-premise = clients les plus rentables inaccessibles
- Zéro validation terrain = construire sur des hypothèses

---

## 7. Roadmap critique (révisée)

> Principe directeur : **une feature n'a de valeur que si elle rend le collègue plus autonome ou les réponses plus fiables.**

---

### Phase 0 — Validation terrain (1 semaine)
**Ne pas construire sur du sable.**

- [ ] 1-2 contacts industrie (responsable maintenance PME)
- [ ] Montrer Phase 1 sur leurs propres documents
- [ ] Écouter ce qui manque selon eux, pas selon nous

---

### Phase 1 — Frontend accessible (2 semaines)
**Objectif : Le collègue peut tout faire sans le développeur.**

Le frontend Phase B passe en priorité absolue — sans lui l'autonomie n'existe pas pour l'utilisateur.

- [ ] Upload multi-documents drag & drop avec progression par fichier
- [ ] `IngestionPlannerAgent` — scan rapide, questions clarification en UI (boutons choix)
- [ ] Progression ingestion visible en temps réel (streaming SSE)
- [ ] Chat agent accessible — zone de texte, réponses streamées
- [ ] Wiki navigable — pages markdown rendues, wikilinks cliquables
- [ ] Graph accessible en 1 clic
- [ ] Interface cron — créer/voir/déclencher les alertes planifiées

---

### Phase 2 — Data layer fiable (3 semaines)
**Objectif : Les données sont fiables, pas juste intelligentes.**

**Wiki structuré**
- [ ] Prompt d'ingestion refondé : JSON typé (specs en tableau, maintenance en tableau)
- [ ] Merge engine champ par champ (pas de réécriture)
- [ ] Graph de confiance par valeur (3 sources = HIGH, 1 source = VÉRIFIER)

**ChromaDB alimenté**
- [ ] `ingest_document_llm()` embed les pages générées
- [ ] Recherche sémantique sur tout le contenu Phase B

**Anti-hallucination**
- [ ] `extract_verifiable_claims()` : regex sur valeurs numériques
- [ ] `verify_claim()` : cross-check wiki + ChromaDB
- [ ] Badge ✅/⚠️ visible dans l'UI sur chaque réponse

---

### Phase 3 — Scale + On-premise (3 semaines)
**Objectif : 100+ documents, clients confidentiels.**

**Ingestion batch**
- [ ] Queue checkpoint JSONL (reprend après crash)
- [ ] Batching 5 docs/appel pour docs courts
- [ ] Priorité : manual_constructor d'abord
- [ ] Temps cible : 100 docs en < 10 minutes (paid tier)

**On-premise**
- [ ] `LLMProvider` interface — switche Mistral API / Ollama selon config
- [ ] Support Mistral 7B/24B local via Ollama
- [ ] `.env` : `LLM_PROVIDER=ollama|mistral`

---

### Phase 4 — HermesBrain + Agents RAG spécialisés (3 semaines)
**Condition : Phases 1-3 terminées et validées sur vrais documents.**

- [ ] `WikiRAGAgent` — wiki structuré + graph-aware + score confiance
- [ ] `ChunkRAGAgent` — ChromaDB sémantique + filtres temporels
- [ ] `HermesBrain` — routing intelligent, synthèse multi-agents
- [ ] `CrossDocRAGAgent` — contradictions à l'échelle

---

### Phase 5 — Production (2 semaines)
- [ ] Auth multi-tenant
- [ ] Tests automatisés (pytest + fixtures docs industriels réels)
- [ ] Monitoring (temps réponse, erreurs LLM, confiance moyenne)

---

## 8. Verdict final

TraceAI répond à un vrai besoin. L'architecture est solide. Mais en l'état c'est un **produit de démo sophistiqué** accessible uniquement par le développeur avec curl.

La vision est juste : un collègue non-technicien dépose des documents, l'agent travaille seul, le collègue pose des questions et obtient des réponses fiables. C'est faisable. Ce n'est pas un fantasme.

**Le chemin :** Frontend accessible → data layer fiable → scale → agents RAG spécialisés.

**La question filtre pour chaque prochaine décision :**
> *"Est-ce que ça rend le collègue plus autonome ou les réponses plus fiables ?"*

Si non — ça attend.
