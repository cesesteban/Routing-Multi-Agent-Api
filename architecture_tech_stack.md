# Arquitectura y Stack Tecnológico - Multi-Agent Routing System (01-PI)

Este documento describe en detalle la arquitectura técnica y las tecnologías utilizadas en el sistema de ruteo multi-agente.

## 1. Stack Tecnológico

El sistema está construido sobre un ecosistema moderno de Python enfocado en escalabilidad y observabilidad de IA:

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Framework Web** | FastAPI | Proporcionar una API REST asíncrona de alto rendimiento. |
| **Orquestación de IA** | LangChain | Manejar la lógica de agentes, cadenas y prompts. |
| **Modelos de Datos** | Pydantic v2 | Validación estricta de entradas y salidas estructuradas de LLMs. |
| **Base de Datos Vectorial** | ChromaDB | Almacenamiento y recuperación de documentos para RAG. |
| **Base de Datos Relacional** | SQLite + SQLAlchemy | Persistencia del historial de consultas y métricas. |
| **Observabilidad** | Langfuse | Trazabilidad completa de ejecuciones, costos y calidad. |
| **Proveedores de LLM** | OpenAI, Groq, Gemini, LM Studio | Versatilidad en el uso de modelos locales y en la nube. |

## 2. Arquitectura de Agentes

El sistema utiliza un patrón de **Orquestación Jerárquica con Bucle de Crítica**:

### A. Capas de Entrada
1. **Context Engineering**: Normaliza la consulta del usuario para mejorar la precisión del ruteo.
2. **Safety Layer**: Verifica patrones adversarios o consultas fuera de scope.

### B. Agente Coordinador (Router)
Utiliza un modelo liviano (Nano LLM) para clasificar la intención del usuario entre varios departamentos (RRHH, Tecnología, Finanzas, etc.) basándose en señales semánticas y razonamiento Chain-of-Thought (CoT).

### C. Agentes Especialistas (Specialists)
Modelos potentes (Powerful LLM) que reciben:
- La consulta original.
- El contexto recuperado vía RAG.
- Instrucciones de rol y tono específicas.
- Feedback del Crítico (en caso de reintento).

### D. Agente Crítico (Auditor)
Actúa como un control de calidad. Valida si la respuesta del especialista:
- Es completa y precisa.
- No contiene placeholders.
- Mantiene el tono adecuado.
Si falla, genera instrucciones de mejora y obliga al especialista a regenerar la respuesta (máximo 3 intentos).

## 3. Implementación de RAG (Retrieval-Augmented Generation)

El sistema utiliza un `RAGManager` que segmenta el conocimiento por departamentos. Utiliza **Búsqueda Híbrida** para maximizar la relevancia:
- **Búsqueda Densa (Semántica)**: Vía ChromaDB para entender el contexto y significado.
- **Búsqueda Léxica (Palabras Clave)**: Vía BM25 para coincidencia exacta de términos técnicos y nombres.
- **Ensemble**: Combina ambos resultados con pesos balanceados (50/50).

**Formatos Soportados**:
- Markdown (`.md`)
- Texto Plano (`.txt`)
- PDF (`.pdf`) mediante `PyPDFLoader`.

Este enfoque asegura respuestas basadas en hechos y minimiza alucinaciones al recuperar información precisa de documentos técnicos.

## 4. Observabilidad y Métricas

Cada ejecución genera un payload enriquecido para desarrolladores:
- **Latencia**: Tiempo total de la cadena (Coordinador + Especialista + Auditoría).
- **Consumo**: Tokens totales acumulados en todas las iteraciones.
- **Trazabilidad**: ID de traza de Langfuse para depuración profunda.
- **Audit Trace**: Historial de qué fue rechazado y por qué durante el proceso de refinamiento.
