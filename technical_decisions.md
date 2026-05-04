# Decisiones Técnicas — Multi-Agent Routing System (03-PI)

Este documento registra las decisiones de diseño arquitectónico tomadas durante el desarrollo del sistema, explicando el razonamiento detrás de cada elección. Sigue un formato inspirado en **Architecture Decision Records (ADR)**: contexto, opciones evaluadas, decisión y consecuencias.

---

## 1. Componentes de LangChain

### ADR-001 — `with_structured_output()` sobre `PydanticOutputParser`

**Contexto**: Los LLMs devuelven texto libre. Necesitábamos que cada agente retornara objetos Pydantic válidos sin código de parseo frágil.

**Opciones evaluadas**:

| Opción | Descripción | Problema |
|---|---|---|
| `PydanticOutputParser` | Parser manual que inyecta instrucciones de formato en el prompt | Frágil si el LLM no sigue el formato exacto; falla con modelos locales débiles |
| `JsonOutputParser` | Parsea JSON libre | Sin validación de schema; los campos opcionales generan bugs silenciosos |
| **`with_structured_output()`** | Pide al LLM que emita JSON estructurado via function calling o instrucciones | ✅ Pydantic v2 valida automáticamente; error temprano y explícito |

**Decisión**: `with_structured_output(PydanticModel)` en todos los agentes.

```python
self.router_llm    = self.nano_llm.with_structured_output(RouterResponse)
self.specialist_llm = self.powerful_llm.with_structured_output(SpecialistResponse)
self.critic_llm    = self.powerful_llm.with_structured_output(CriticResponse)
self.evaluator_llm = self.powerful_llm.with_structured_output(EvaluatorResponse)
```

**Consecuencias**:
- ✅ Cero código de parseo — la validación es responsabilidad de Pydantic
- ✅ Si el LLM genera un campo inválido, la excepción es clara y trazable
- ⚠️ Modelos locales muy pequeños (< 7B params) pueden no seguir el schema — se mitiga con prompts explícitos

---

### ADR-002 — `ChatPromptTemplate.from_template()` con archivos Markdown

**Contexto**: Los prompts son el núcleo del comportamiento de cada agente. Necesitaban ser versionables, editables sin tocar código, y fáciles de iterar.

**Opciones evaluadas**:

| Opción | Problema |
|---|---|
| Strings en el código fuente | No versionables independientemente; mezclan lógica con contenido |
| Variables de entorno | Difíciles de mantener para prompts largos |
| **Archivos `.md` en `prompts/`** | ✅ Editables, versionables en git, legibles por humanos |

**Decisión**: Cada agente carga su prompt desde un archivo Markdown en runtime:

```python
with open("prompts/router_prompt.md", "r", encoding="utf-8") as f:
    template_text = f.read()
prompt = ChatPromptTemplate.from_template(template_text)
```

**Consecuencias**:
- ✅ Prompt engineering sin deployar código nuevo
- ✅ Git muestra diffs claros de cambios en el comportamiento de los agentes
- ⚠️ El archivo debe estar disponible en el sistema de archivos; en contenedores se copia al build (`COPY . .`)

---

### ADR-003 — Dos modelos LLM diferenciados (Nano + Powerful)

**Contexto**: No todos los pasos del pipeline requieren el mismo poder computacional.

**Decisión**: Jerarquía de dos modelos:

```
Nano LLM  → Router, SafetyGuard L2    (velocidad, costo bajo)
Powerful LLM → Specialist, Critic, Evaluator (calidad, razonamiento profundo)
```

**Razonamiento**:

| Agente | Por qué Nano | Por qué Powerful |
|---|---|---|
| Router | Clasificar 5 intenciones es simple | — |
| Safety L2 | Detección binaria con contexto | — |
| Specialist | — | Respuesta experta con CoT complejo |
| Critic | — | Auditoría técnica con razonamiento multicriteria |
| Evaluator | — | Scoring multidimensional con justificación |

**Consecuencias**:
- ✅ Reducción de costos estimada en ~60% vs. usar el modelo potente para todo
- ✅ El Router responde en < 300ms (Nano es rápido)
- ⚠️ Si el Nano clasifica mal, toda la cadena trabaja sobre un intent incorrecto — se mitiga con CoT de 4 pasos en el Router

---

### ADR-004 — Orquestación manual vs. LangGraph

**Contexto**: El flujo tiene ciclos (Specialist ↔ Critic). LangGraph es la herramienta de LangChain para grafos de agentes con estado.

**Opciones evaluadas**:

| Opción | Pros | Contras |
|---|---|---|
| **Python secuencial (`routing_service.py`)** | Simple, testeable, sin deps extra | Branching complejo requiere más código |
| LangGraph | Visualización de grafo, streaming nativo, human-in-the-loop | Complejidad adicional, curva de aprendizaje, harder to mock en tests |
| LangChain Agents (ReAct) | Flexible para tool calling | No determinista — el LLM decide cuándo y qué herramienta usar |

**Decisión**: Orquestación secuencial en Python puro.

**Razonamiento**: El flujo actual tiene exactamente **1 rama condicional** (el while loop Specialist ↔ Critic). LangGraph aporta valor cuando hay:
- Paralelismo real entre nodos (fan-out)
- Human-in-the-loop con checkpointing
- Conversación multi-turno con memoria persistente

Ninguna de estas features se requiere en la iteración actual. Se añadirá LangGraph cuando cualquiera de esas features sea prioridad.

---

## 2. Estrategia de Routing

### ADR-005 — Router LLM vs. Clasificador tradicional (embeddings/ML)

**Contexto**: El sistema necesita clasificar consultas en 5 departamentos. Existen múltiples enfoques.

**Opciones evaluadas**:

| Enfoque | Precisión | Costo | Latencia | Mantenimiento |
|---|---|---|---|---|
| Palabras clave / regex | Baja (muchos falsos negativos) | ~0 | < 1ms | Alto (lista manual) |
| Embeddings + cosine similarity | Media-Alta | Bajo | ~50ms | Medio (requiere ejemplos etiquetados) |
| Clasificador ML (SVM, XGBoost) | Alta | Bajo | ~10ms | Alto (dataset, reentrenamiento) |
| **LLM Router con CoT** | Muy Alta | Medio | ~300ms | Bajo (prompt engineering) |

**Decisión**: LLM Router con Chain-of-Thought de 4 pasos.

**Razonamiento**:
- Las consultas empresariales son **ambiguas por naturaleza**: "Problema con mi tarjeta" puede ser FINANZAS o TECNOLOGIA según el contexto.
- El CoT fuerza al modelo a razonar explícitamente antes de clasificar, lo que reduce errores de clasificación en casos límite.
- El `RouterResponse` incluye `confidence` y `reason`, lo que habilita monitoreo y auditoría de las decisiones de ruteo.

```python
class RouterResponse(BaseModel):
    chain_of_thought: List[str]  # 4 pasos de razonamiento explícito
    intent: str                   # RRHH | TECNOLOGIA | FINANZAS | RECLAMOS | GENERAL
    confidence: float             # 0.0 – 1.0
    reason: str                   # justificación auditable
```

**Consecuencias**:
- ✅ Maneja ambigüedad semántica que regex/embeddings simples no pueden
- ✅ El `reason` es trazable en Langfuse y útil para detectar errores de routing
- ⚠️ +300ms de latencia vs. clasificador ML — aceptable para el caso de uso (soporte empresarial)
- ⚠️ Dependiente de la calidad del prompt — un cambio en `router_prompt.md` puede degradar el routing

---

### ADR-006 — Bucle Specialist ↔ Critic con máximo 3 intentos

**Contexto**: Un solo paso de generación no garantiza calidad. Se necesita un mecanismo de auto-corrección.

**Opciones evaluadas**:

| Estrategia | Descripción | Problema |
|---|---|---|
| Un solo paso | Genera y publica sin revisión | Sin garantía de calidad |
| Self-reflection | El mismo modelo revisa su propia respuesta | Sesgo de confirmación: el modelo tiende a validar lo que generó |
| **Critic separado** | Un agente diferente con prompt de auditor | ✅ Perspectiva externa, criterios distintos |
| Ensemble + voting | Múltiples modelos votan | Costo y complejidad muy alto |

**Decisión**: Critic separado con feedback estructurado, máximo 3 intentos.

**Razonamiento del límite de 3**:
- Intento 1: generación inicial
- Intento 2: corrección de issues del Crítico
- Intento 3: si sigue fallando, el error probablemente es estructural (prompt o contexto insuficiente)

Más de 3 intentos generaría latencia inaceptable (> 4 segundos) sin garantía de mejora marginal.

**Consecuencias**:
- ✅ La calidad promedio es significativamente mayor que sin el loop
- ✅ El `audit_trace` en la DB registra cada rechazo y sugerencia para análisis post-hoc
- ⚠️ En el worst case (3 rechazos), la latencia se triplica

---

### ADR-007 — Routing determinista de Tools (no function calling)

**Contexto**: Las herramientas externas (Jira, Slack, Email, Calendar, KB) necesitan ejecutarse tras la respuesta del especialista.

**Opciones evaluadas**:

| Enfoque | Descripción | Problema |
|---|---|---|
| **LLM function calling** | El LLM decide qué tools activar | No determinista; puede alucinar argumentos o activar tools incorrectas |
| **ToolExecutor determinista** | Reglas explícitas basadas en metadata | ✅ Predecible, testeable, sin riesgo de alucinaciones |

**Decisión**: `ToolExecutor` basado en reglas sobre la `SpecialistResponse`:

```
si to_email                            → EmailTool
si priority ∈ {ALTA, CRÍTICA}          → SlackTool + JiraTool
si requires_supervisor                 → CalendarTool
si evaluation_score ≥ 0.7             → KBUpdaterTool
```

**Razonamiento**: Las herramientas tienen efectos externos reales (crean tickets, envían emails). Delegar esa decisión al LLM introduce riesgo de ejecución accidental. Las reglas deterministas son auditables, versionables en código y 100% testeables.

---

## 3. Configuración de RAG

### ADR-008 — RAG Híbrido (ChromaDB + BM25) vs. RAG puro vectorial

**Contexto**: Un sistema RAG puro vectorial (solo embeddings) tiene debilidades conocidas en ciertos casos.

**Problema del RAG vectorial puro**:
```
Query:  "Error código 0x80004005 en VPN"
Vector: encuentra documentos sobre "problemas de conectividad" (semánticamente cercanos)
        pero NO encuentra el documento que contiene "0x80004005" porque es un código opaco
        sin representación semántica útil en el embedding space
```

**Solución**: Fusión de dos retrievers:

| Retriever | Fortaleza | Debilidad |
|---|---|---|
| ChromaDB (denso) | Entiende significado y contexto | Falla con términos técnicos opacos, siglas, IDs |
| BM25 (léxico) | Encuentra términos exactos | No entiende paráfrasis ni sinónimos |
| **RRF combinado** | Cubre ambas debilidades | — |

**Decisión**: `HybridRetriever` propio con Reciprocal Rank Fusion.

---

### ADR-009 — Reciprocal Rank Fusion (RRF) vs. score fusion lineal

**Contexto**: Para combinar los resultados de ChromaDB y BM25 se necesita una función de fusión.

**Opciones evaluadas**:

| Método | Fórmula | Problema |
|---|---|---|
| **Score fusion lineal** | `α · score_vector + β · score_bm25` | Las escalas de score son incomparables entre retrievers |
| **RRF** | `Σ weight_i / (k + rank_i(doc))` | ✅ Solo usa el rango, no el score — invariante a la escala |
| Cross-encoder reranking | Modelo adicional que re-puntúa todos los resultados | Latencia muy alta (+500ms) para ganancia marginal |

**Decisión**: RRF con `k=60` y pesos `0.7 (vectorial) / 0.3 (BM25)`.

```python
# RRF score para cada documento
for rank, doc in enumerate(vector_results):
    scores[doc.page_content] += weights[0] / (k + rank)
for rank, doc in enumerate(bm25_results):
    scores[doc.page_content] += weights[1] / (k + rank)
```

**Razonamiento de los pesos 70/30**:
- Las consultas empresariales son mayormente semánticas ("¿cómo solicito vacaciones?")
- Los casos técnicos con IDs/códigos específicos son la minoría
- 70/30 da prioridad al significado sin sacrificar la exactitud léxica

**Razonamiento de `k=60`**:
- Valor estándar de la literatura de IR (Cormack et al., 2009)
- Controla el peso relativo de las posiciones bajas del ranking: `k` alto → posiciones bajas importan más

**Por qué NO se usó `EnsembleRetriever` de LangChain**:
- Dependencia frágil que generó `ModuleNotFoundError` en LangChain >= 0.3.x
- La implementación propia de `HybridRetriever` es ~50 líneas, completamente testeable y sin dependencias externas

---

### ADR-010 — Segmentación del RAG por departamento

**Contexto**: La base de conocimiento incluye documentos de RRHH, Tecnología, Finanzas, Reclamos y Seguridad. Se podría usar un único índice vectorial o uno por departamento.

**Opciones evaluadas**:

| Estrategia | Descripción | Problema |
|---|---|---|
| Índice único con metadata filtering | Un ChromaDB con filtro por `department` | Contaminación semántica cross-departamento |
| **Índice por departamento** | Un RAGManager con un retriever por departamento | ✅ Contexto puro y relevante por dominio |

**Decisión**: `RAGManager` crea un retriever independiente por departamento:

```python
# Solo indexa los documentos del departamento detectado por el Router
context = self.rag.retrieve_context(query, routing.intent)
#                                          ↑ "TECNOLOGIA" → solo doc de /data/tecnologia/
```

**Consecuencias**:
- ✅ Sin riesgo de que un documento de RRHH contamine la respuesta a una consulta técnica
- ✅ Los vectorstores son más pequeños → búsqueda más rápida
- ⚠️ Si el Router clasifica mal la intención, el RAG busca en el índice equivocado

---

### ADR-011 — Chunk size 500 con overlap 50

**Contexto**: Los documentos PDF/Markdown se fragmentan antes de indexar. El tamaño del chunk afecta directamente la calidad del contexto recuperado.

**Trade-offs**:

| Chunk size | Ventaja | Desventaja |
|---|---|---|
| Pequeño (< 200 tokens) | Más preciso — menos ruido por chunk | Pierde contexto necesario para responder (una respuesta puede estar en 2 chunks separados) |
| **Mediano (500 tokens)** | Balance entre precisión y contexto completo | — |
| Grande (> 1000 tokens) | Contexto rico | Chunks irrelevantes contaminan el prompt del especialista |

**Decisión**:
```python
RAG_CHUNK_SIZE    = 500   # ~375 palabras — un párrafo denso completo
RAG_CHUNK_OVERLAP = 50    # 10% de overlap para no cortar oraciones en el límite
```

**Consecuencias**:
- ✅ Los procedimientos de RRHH (ej: "proceso de solicitud de vacaciones") caben en 1-2 chunks
- ⚠️ Para documentos técnicos con tablas o código, puede ser necesario ajustar a 800 tokens

---

## 4. Seguridad

### ADR-012 — Safety bicapa (L1 patterns + L2 LLM) vs. solo LLM

**Contexto**: Proteger el sistema contra prompt injection, jailbreaking y consultas fuera de scope.

**Opciones evaluadas**:

| Estrategia | Descripción | Problema |
|---|---|---|
| Solo LLM safety | Delegar toda la detección al modelo | Costo de tokens en cada query; latencia adicional para queries legítimas |
| Solo patterns | Lista de strings prohibidos | No detecta ataques semánticos disfrazados |
| **Bicapa L1 + L2** | Patterns primero (gratis), LLM solo si L1 pasa | ✅ Costo-eficiente y robusto |

**Decisión**: Embudo de costo-eficiencia:

```
Query → [L1: pattern matching, 0 tokens, < 1ms]
              ↓ si pasa
         [L2: Nano LLM + RAG de políticas de seguridad]
              ↓ si pasa
         [Router Agent]
```

**Consecuencias**:
- ✅ El 95% de los ataques obvios se bloquean sin consumir tokens
- ✅ L2 detecta ataques semánticos que L1 no ve
- ⚠️ L2 depende de que `data/seguridad/` tenga documentos de políticas indexados; sin ellos, el LLM razona sin contexto

---

## 5. Observabilidad

### ADR-013 — Traza raíz unificada en Langfuse

**Contexto inicial**: Cada `chain.invoke()` creaba su propia traza en Langfuse. Los scores del Evaluador se enviaban sin `trace_id` → scores huérfanos.

**Problema identificado**:
```
Langfuse (antes):
  Trace A  ← router chain.invoke()
  Trace B  ← specialist chain.invoke()
  Trace C  ← critic chain.invoke()
  Trace D  ← evaluator chain.invoke()
  Score 0.87  ← sin trace_id — no linkeable a ninguna ejecución
```

**Decisión**: Crear una traza raíz por `process_query()` y propagar el `trace_id`:

```python
# routing_service.py
trace = langfuse_client.trace(name="process_query", input={"query": ...})
trace_id = trace.id

# Cada agente usa CallbackHandler(trace_id=trace_id) → span hijo
# Evaluator usa langfuse_client.score(trace_id=trace_id, value=...)
```

**Resultado**:
```
Langfuse (después):
  Trace "process_query" (trace_id=abc123)
    ├── Span: router
    ├── Span: specialist
    ├── Span: critic
    ├── Span: evaluator
    └── Score 0.87  ← vinculado a trace_id=abc123 ✅
```

**Consecuencias**:
- ✅ Dashboard de Langfuse muestra el flujo completo de cada query como una unidad
- ✅ Se puede correlacionar `evaluation_score` con latencia, número de intentos e intent del router
- ✅ Los scores son filtrables por departamento, prioridad y score threshold

---

## 6. Testing

### ADR-014 — Tests E2E con DB in-memory y LLM mockeado

**Contexto**: Los tests deben ser rápidos, reproducibles y ejecutables sin credenciales de LLM o una DB real.

**Decisión**: Stack de testing aislado:

```python
# 1. DB: SQLite in-memory (no PostgreSQL, no archivos)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 2. LLM: MultiAgentSystem mockeado con respuestas fijas
mock_system.route_query.return_value = {
    "data": RouterResponse(intent="TECNOLOGIA", confidence=0.95, ...)
}

# 3. Cliente: httpx AsyncClient contra ASGI (sin servidor real)
transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as ac:
    ...
```

**Consecuencias**:
- ✅ 75 tests corren en ~1.5s dentro de Docker sin ninguna API key
- ✅ Tests completamente deterministas — el mock siempre retorna el mismo `RouterResponse`
- ⚠️ Los tests no validan la calidad de los prompts ni el comportamiento real del LLM — eso es responsabilidad de Langfuse + evaluación manual
