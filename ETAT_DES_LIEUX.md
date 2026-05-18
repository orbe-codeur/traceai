# TraceAI — État des Lieux Critique
> Rédigé le 2026-05-18. Document interne. Brutal et honnête.

---

## 1. Ce qu'on veut faire

Construire un système de knowledge management pour la maintenance industrielle capable de :

1. Ingérer des centaines de documents techniques hétérogènes (manuels constructeurs, rapports d'intervention, fiches techniques, inventaires pièces, docs scannés)
2. Construire automatiquement une base de connaissances structurée par machine
3. Détecter les contradictions entre sources, maintenir un graphe de confiance par valeur
4. Répondre aux questions des techniciens avec citations vérifiables et score de fiabilité
5. Fonctionner en local (on-premise) pour des clients industriels sensibles aux données
6. Scaler à 500-1000 documents sans dégradation de qualité

La cible : PME industrielles (50-500 employés), responsables maintenance, ingénieurs fiabilité. Secteurs : manufacturier, énergie, process industriel.

---

## 2. Ce qu'on a réellement

### Ce qui fonctionne (testé, validé)

**Phase 1 — Checklist PDF** ✅
- Extraction 3 passes (TOC → chunks → merge) sur manuels de 50-120 pages
- Traçabilité complète (qui, quand, note, témoin)
- Export PV HTML
- Validé sur Jenny Compressor 54 pages → 126 étapes
- C'est le seul feature qui a vu un vrai document

**Agent core Hermes** ✅
- Boucle tool calling, 15 itérations max
- Mémoire persistante SQLite FTS5
- Skills auto-générés post-tour
- Continuité cross-session
- Background review (fork daemon)
- Streaming SSE
- Cron engine

**Wiki LLM** ✅ (en théorie)
- `ingest_document_llm()` → one-call Mistral-large
- `health_check()`, `lint_wiki()`, `heal_missing_entities()`
- Knowledge graph Pass1 (regex) + Pass2 (LLM)
- Visualisation vis.js

### Ce qui existe mais est cassé ou inutilisable

**ChromaDB** ❌
Présent dans le code. Jamais alimenté par les pages wiki Phase B.
`search_chunks` appelle ChromaDB mais les documents ingérés via `ingest_document_llm()` ne sont **jamais embeddés**. La recherche sémantique est aveugle sur 100% du contenu Phase B.

**Wiki structuré** ❌
Les pages générées sont du **LLM prose**. Pas de tableaux typés, pas de champs vérifiables, pas de merge logique. Si tu ingères un 2ème document qui contredit le premier, la page est réécrite — tu perds la contradiction.

**Frontend Phase B** ❌
Tout ce qu'on a construit depuis 3 sessions (wiki-ingest, orchestrateur, streaming, cron, graph) est accessible **uniquement en curl**. Un technicien ne peut pas s'en servir.

**Multi-document** ❌
Le système n'a été testé qu'avec **un seul document** (Jenny Compressor Manual). On ne sait pas si l'ingestion de 10 documents sur la même machine produit un wiki cohérent ou une soupe contradictoire.

**Anti-hallucination** ❌
Aucune vérification post-génération. Les valeurs numériques (couples, pressions, fréquences) ne sont pas cross-checkées contre les sources. Pour un technicien qui suit une instruction fausse sur une installation critique — c'est un risque réel.

---

## 3. Pourquoi c'est pas bien

### 3.1 Le problème fondamental : couche data cassée, architecture belle

On a bâti une architecture d'agents sophistiquée (Hermes brain, delegate_task, background review, curator, cron, streaming) sur une **couche data qui ne tient pas**.

```
Ce qu'on a construit :    Ce dont on a besoin :
Architecture élégante  ←→  Données fiables
     ✅                         ❌
```

WikiRAGAgent, ChunkRAGAgent, GraphRAGAgent — tous ces agents spécialisés qu'on envisage présupposent :
- Un wiki structuré en tableaux typés → pas là
- ChromaDB alimenté → pas là
- Un graph dense → 17 nœuds sur 1 document

On optimise la logistique avant d'avoir la marchandise.

### 3.2 Zéro validation terrain

**On n'a jamais mis le produit devant un vrai technicien.**

Phase 1 est validée techniquement. Elle n'est pas validée métier. Est-ce que les techniciens comprennent l'interface ? Est-ce qu'ils font confiance aux étapes extraites ? Est-ce que le PV HTML correspond à ce qu'ils doivent remettre ?

On construit Phase B, Phase B+, orchestrateur multi-agents... sur des hypothèses non validées sur Phase 1.

### 3.3 Dispersion technique

En une session on a implementé :
- Context compressor
- Background review
- Curator
- Orchestrateur + delegate_task
- Cron engine
- Streaming SSE

**Aucun de ces 6 features ne répond au vrai problème :** la qualité et la fiabilité des réponses sur des documents industriels réels.

Ce sont des features d'infrastructure qui rendent l'agent plus autonome. L'agent est maintenant Hermes-grade. Mais il répond avec des données non structurées sur un seul document de test.

### 3.4 Le problème on-premise non adressé

Les clients industriels visés (manufacturier, énergie, process) ne vont **pas** envoyer leurs données techniques à l'API Mistral cloud. Plans de maintenance, données de pannes, schémas machines — c'est confidentiel.

On a zéro stratégie on-premise. Pas d'Ollama, pas d'abstraction LLM qui switche selon la config. C'est un **deal breaker commercial** sur 60-70% du marché cible.

### 3.5 Pas de tests automatisés

Sur un système qui fait des recommandations techniques potentiellement safety-critical — **zéro test automatisé**. Chaque validation est un curl manuel. Si on refactore `wiki_engine.py` demain, on ne sait pas ce qu'on a cassé.

---

## 4. Les agents — description et évaluation honnête

### Agents existants

| Agent | Rôle | Qualité réelle |
|---|---|---|
| `TraceAIAgent` | Boucle principale Hermes | ✅ Solide. Bien adapté. |
| `TraceAIOrchestratorAgent` | Délègue via delegate_task | ⚠️ Existe mais sous-utilisé. L'agent ne délègue pas spontanément. |
| `BackgroundReview` | Fork post-tour, update skills/mémoire | ⚠️ Fonctionne mais déclenché rarement (budget >= 3). |
| `Curator` | Maintenance skills périodique | ⚠️ Overkill pour 7 skills actuels. Utile à 50+ skills. |
| `CronScheduler` | Jobs planifiés | ✅ Fonctionne. Valeur réelle pour alertes nocturnes. |

### Agents planifiés (non construits)

| Agent | Utilité réelle | Prérequis non remplis |
|---|---|---|
| `WikiRAGAgent` | Élevée si wiki structuré | Wiki en prose → résultats médiocres |
| `ChunkRAGAgent` | Élevée si ChromaDB alimenté | ChromaDB vide pour Phase B |
| `GraphRAGAgent` | Moyenne | Graph trop petit (1 doc) |
| `MemoryRAGAgent` | Faible (déjà dans search_memory) | — |
| `CrossDocRAGAgent` | Élevée pour 100+ docs | Aucun des prérequis |
| `IngestionPlannerAgent` | Élevée pour 100+ docs | Peut être construit maintenant |
| `HermesBrain` (routing) | Élevée si agents RAG solides | Tous les agents RAG inexistants |

**Verdict agents :** On a 5 agents d'infrastructure. On a 0 agents RAG spécialisés. On planifie 6 agents RAG + 1 cerveau sur une couche data cassée.

---

## 5. A-t-on des chances de réussir ?

**Oui, mais sous conditions.**

### Ce qui joue en notre faveur

Le problème est réel et mal adressé par les acteurs existants. Aucun GMAO ne fait "knowledge graph + agent qui répond aux questions avec citations" pour des PME industrielles.

L'architecture Hermes est solide. Les patterns d'autonomie sont en place. C'est une vraie fondation, pas du prototype.

Phase 1 (checklist PDF) est vendable maintenant. C'est un produit simple, concret, compréhensible. Il peut financer la suite.

### Ce qui nous met en danger

**Si on continue à construire de l'infrastructure sans valider la data layer et le terrain**, on aura dans 3 mois un système de 15 agents sophistiqués qui répond mal parce que le wiki est du LLM prose non vérifié.

**Si on n'adresse pas le on-premise**, on perd les clients les plus rentables avant d'avoir commencé à les approcher.

**Si on n'a pas de tests automatisés**, une refacto du wiki_engine casse silencieusement tout et on ne le sait qu'en démo client.

**Probabilité de succès estimée :**
- Avec le chemin actuel (continuer l'infrastructure) : **30%**
- En pivotant sur data layer + validation terrain + on-premise : **70%**

---

## 6. Est-ce qu'on se disperse trop ?

**Oui, clairement.**

On a 3 chantiers ouverts simultanément :
1. Infrastructure agent (Hermes patterns) → avancé
2. Wiki LLM (data layer) → incomplet
3. Architecture RAG spécialisée (agents RAG) → non commencé

Un produit industriel qui sera mis entre les mains de techniciens sur des machines réelles a besoin de **fiabilité** avant de la sophistication architecturale.

Le contexte compressor, le curator, l'orchestrateur — ce sont de bonnes idées. Mais elles n'apportent pas de valeur tant que le wiki génère du LLM prose non vérifié.

**Règle simple à appliquer :** une feature n'est utile que si elle améliore la qualité ou la fiabilité des réponses sur des documents industriels réels. Tout le reste est prématuré.

---

## 7. Roadmap critique

### Phase 0 — Stop building, start validating (1 semaine)
**Objectif : Ne pas construire sur du sable.**

- [ ] Trouver 1-2 contacts dans l'industrie (responsable maintenance PME)
- [ ] Leur montrer Phase 1 (checklist PDF) sur leurs propres documents
- [ ] Écouter ce qui manque *selon eux*, pas selon nous
- [ ] Ne pas construire Phase B tant que Phase 1 n'est pas validée terrain

**Pourquoi c'est critique :** Si Phase 1 ne résout pas un vrai problème pour un vrai technicien, tout ce qu'on construit dessus est inutile.

---

### Phase 1 — Fix the data layer (3 semaines)
**Objectif : Que les données soient fiables avant d'être intelligentes.**

**Semaine 1 — Wiki structuré**
- [ ] Refondre le prompt d'ingestion : JSON typé (specs en tableau, maintenance en tableau)
- [ ] Merge engine champ par champ (pas de réécriture complète)
- [ ] Graph de confiance par valeur (3 sources = HIGH, 1 source = LOW)
- [ ] Tests automatisés sur `wiki_engine.py`

**Semaine 2 — ChromaDB alimenté**
- [ ] `ingest_document_llm()` → embed les pages générées dans ChromaDB
- [ ] `search_chunks` et `search_wiki` utilisent les mêmes embeddings
- [ ] Tests de cohérence recherche sémantique vs keyword

**Semaine 3 — Anti-hallucination**
- [ ] `extract_verifiable_claims()` : regex sur valeurs numériques + unités
- [ ] `verify_claim()` : cross-check contre wiki structuré + ChromaDB
- [ ] `annotate_response()` : `confidence` + `warning` dans la réponse API
- [ ] Frontend affiche ⚠️ sur les claims non vérifiés

---

### Phase 2 — Frontend Phase B (2 semaines)
**Objectif : Un technicien peut utiliser toutes les features AI sans curl.**

- [ ] Bouton "Wiki Intelligent" dans Phase2IngestView → déclenche `wiki-ingest`
- [ ] Onglet wiki navigable avec pages markdown rendues + wikilinks cliquables
- [ ] Chat avec streaming SSE visible dans l'UI
- [ ] Badges confiance sur les réponses (⚠️ non vérifié / ✅ vérifié)
- [ ] Page graph.html accessible en 1 clic
- [ ] Interface cron : créer/voir/déclencher les jobs planifiés

---

### Phase 3 — Scale (3 semaines)
**Objectif : Tenir à 100+ documents sans dégradation.**

**Ingestion batch**
- [ ] Queue avec checkpoint JSONL (reprend après crash)
- [ ] Batching 5 docs/appel sur `intervention_report` et `parts_inventory`
- [ ] Priorité : `manual_constructor` d'abord, `unknown` en dernier
- [ ] Workers parallèles respectant les rate limits

**On-premise**
- [ ] Abstraction LLM (`LLMProvider` interface) dans `agents/utils.py`
- [ ] Support Ollama + Mistral 7B/24B local
- [ ] Config via `.env` : `LLM_PROVIDER=ollama|mistral`
- [ ] Tests de régression avec modèle local

**IngestionPlannerAgent**
- [ ] Scan rapide collection (zéro LLM) → inventaire types + machines
- [ ] Questions utilisateur via `ask_clarification` pour lever les ambiguïtés
- [ ] Plan d'ingestion priorisé avant exécution

---

### Phase 4 — HermesBrain + Agents RAG spécialisés (3 semaines)
**Objectif : Architecture cible avec cerveau + agents spécialisés.**
**Condition : Phase 1-3 terminées et validées.**

- [ ] `WikiRAGAgent` (wiki structuré + graph-aware)
- [ ] `ChunkRAGAgent` (ChromaDB sémantique + filtres temporels)
- [ ] `GraphRAGAgent` (traversal + communautés)
- [ ] `HermesBrain` avec routing intelligent
- [ ] Parallélisation native via `delegate_task`
- [ ] CrossDocRAGAgent pour contradictions à l'échelle

---

### Phase 5 — Production readiness (2 semaines)
**Objectif : Mettre devant de vrais clients.**

- [ ] Auth multi-tenant (par site client)
- [ ] Suite de tests automatisés (pytest + fixtures docs industriels)
- [ ] Documentation API + guide d'installation
- [ ] Monitoring basique (temps de réponse, erreurs LLM, confiance moyenne)
- [ ] Pricing model validé

---

## 8. Verdict final

TraceAI a une bonne vision et une architecture technique solide. Mais en l'état, c'est un **produit de démo sophistiqué**, pas un outil industriel.

Le chemin critique est : **data layer → terrain → scale → agents RAG**.

Si on continue dans l'ordre actuel (infrastructure agent avant data layer), on risque d'arriver à la Phase 4 avec le cerveau Hermes le plus sophistiqué du marché... qui répond avec des données non fiables.

**La question à se poser avant chaque session :**
> "Est-ce que cette feature améliore la fiabilité des réponses sur des documents industriels réels ?"

Si la réponse est non — attendre Phase 1 et 2.
