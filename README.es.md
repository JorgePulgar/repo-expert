# Repo Expert

> 🇬🇧 English? Read [`README.md`](README.md).

**RAG agéntico que responde preguntas sobre cualquier repositorio de GitHub al que se le
apunte, con citas en línea.** Una sola base de código, dos instancias seleccionadas por
configuración — sin cambios de código para alternar:

- **public** — entregable de clase apuntado a un repositorio público serio
  (`fastapi/fastapi`).
- **portfolio** — demo para reclutadores apuntada a los repositorios de portafolio de
  Jorge Pulgar + una Base de Conocimiento de Carrera (Career KB).

Stack: Azure AI Search (híbrido + reordenador semántico, base de conocimiento Foundry IQ) ·
LangGraph (RAG correctivo/agéntico) · FastAPI · Azure OpenAI. Python 3.12, gestionado con
[uv](https://docs.astral.sh/uv/).

## Qué hace

Un endpoint `/ask` de FastAPI entrega la pregunta a un agente **LangGraph** que
enruta → recupera → genera con citas → autoverifica la fundamentación → reintenta con un
fallback si la respuesta no está respaldada. La recuperación se ejecuta sobre una **base de
conocimiento Foundry IQ** en Azure AI Search construida a partir de nuestros propios
índices con fragmentación personalizada. El agente es el dueño del razonamiento; el
servicio gestionado es el dueño de la recuperación (build-vs-buy — ver
[`ARCHITECTURE.md`](ARCHITECTURE.md)).

## Qué conocimiento tiene — tres fuentes heterogéneas

| # | Fuente | public | portfolio |
|---|---|---|---|
| 1 | Documentación / markdown (en la KB) | Docs de FastAPI + README | Markdown de los repos de portafolio |
| 2 | Código fuente (en la KB, fragmentado por símbolo) | `fastapi/**/*.py` | Python de los repos de portafolio |
| 3 | **Intercambiada por instancia** | **Issues/PRs de GitHub** — en vivo vía API | **Career KB** — indexada en la KB |

La tercera fuente difiere en *tipo* (herramienta de API en vivo vs fuente de conocimiento
indexada), cumpliendo el requisito de ≥3 fuentes heterogéneas. La instancia activa se elige
por completo mediante configuración (`src/repo_expert/config/instance.py`); ver
[`ARCHITECTURE.md`](ARCHITECTURE.md) para el diseño completo.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestiona Python 3.12 automáticamente).
- Azure AI Search (con capacidad de recuperación agéntica) + deployments de Azure OpenAI.
  Se necesita un token de GitHub solo para la fuente de issues en vivo de la instancia
  public. Pasos de aprovisionamiento: [`docs/setup.md`](docs/setup.md).

## Instalación

```bash
uv sync                      # instala dependencias en .venv
cp .env.example .env         # luego completa las claves de Azure + GitHub
```

Selecciona la instancia en `.env` (o por comando con `--instance`):

```bash
REPO_EXPERT_INSTANCE=public   # o: portfolio
```

Las claves requeridas están documentadas en [`.env.example`](.env.example). La
configuración falla rápido: una variable requerida ausente lanza un error al arranque
nombrando la variable problemática.

## Ejecución

```bash
# 1. Construir la base de conocimiento desde el/los repo(s) objetivo
uv run repo-expert ingest
uv run repo-expert --instance portfolio ingest   # instancia portfolio

# 2. Servir la API (GET /health, POST /ask; docs interactivas en /docs)
uv run uvicorn repo_expert.api.app:app --reload

# 3. Preguntar
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "¿Cómo maneja FastAPI la inyección de dependencias?"}'
```

`GET /health` reporta la instancia activa, el repositorio objetivo y los conteos de
documentos por índice.

## Desarrollo

```bash
uv run ruff check .          # lint
uv run pytest                # tests unitarios (los de integración necesitan .env: -m integration)
```

## Evaluación

Un conjunto curado de preguntas/respuestas mide las dos cosas que importan en un RAG
agéntico: **relevancia de recuperación** y **fundamentación (groundedness)**. Regenerar con
`uv run repo-expert eval` (añade `--instance portfolio` para el conjunto de portafolio).

**Método**
- *Relevancia de recuperación* — por pregunta: (a) **exactitud de enrutamiento**, ¿eligió
  el router la(s) fuente(s) esperada(s); (b) **hit@k**, ¿coincidió un resultado top-k de la
  fuente esperada con la cita esperada (subcadena de archivo/sección) y el tipo.
- *Fundamentación* — se ejecuta el agente completo y luego un **juez LLM independiente**
  evalúa si cada afirmación de la respuesta está respaldada por evidencia recuperada de
  forma independiente. También se registra la propia bandera de autofundamentación del
  agente.

**Instancia public** (`fastapi/fastapi`, n=16 — 5 código, 7 docs, 3 issues, 1 multi-salto):

| Métrica | Valor |
| --- | --- |
| Exactitud de enrutamiento | **1.00** |
| Relevancia hit@6 | **0.88** (docs 1.0 · código 0.6 · issues 1.0 · mixto 1.0) |
| Tasa de fidelidad (juez) | **0.75** |
| Puntaje medio de fidelidad | **0.89** |
| Tasa de autofundamentación del agente | **0.88** |

Reporte completo: [`docs/eval-results-public.md`](docs/eval-results-public.md).

**Instancia portfolio** (n=10, preguntas de carrera + repos de portafolio): **enrutamiento
1.0, relevancia hit@6 1.0, fidelidad 1.0**
([`docs/eval-results-portfolio.md`](docs/eval-results-portfolio.md)). Las preguntas fuera
de tema son rechazadas por la barrera de alcance configurable.

**Análisis / limitaciones**
- La recuperación de docs e issues es fuerte (1.0); el hit@6 global es 0.88.
- La recuperación de issues usa una **reescritura de consulta por LLM**: las preguntas en
  prosa se condensan a palabras clave porque la Search API de GitHub usa AND entre términos
  y no devuelve nada para prosa. Esto subió la relevancia de issues de 0.0 → 1.0.
- Relevancia de código 0.6: los archivos de símbolos exactos no siempre están en el top-k;
  la fragmentación por símbolo + reordenamiento resuelve la mayoría, pero no todas, las
  búsquedas de "dónde se define X".
- El bucle correctivo atrapa borradores débiles antes de responder. La tasa de fidelidad de
  public es más baja que una línea base solo-KB precisamente *porque* el agente ahora
  intenta respuestas sustantivas de issues en lugar de recurrir a la KB — un intercambio
  deliberado de cautela por cobertura.
- La fundamentación usa un juez LLM (gpt-4o), por lo que los puntajes tienen pequeña
  varianza entre ejecuciones.

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — componentes, flujo de datos, grafo del agente,
  decisiones.
- [`docs/setup.md`](docs/setup.md) — aprovisionamiento de Azure.
- [`docs/deploy.md`](docs/deploy.md) — build del contenedor + despliegue en Azure.
- [`docs/phases/README.md`](docs/phases/README.md) — registro de desarrollo fase por fase.

## Licencia

Para fines de curso y demostración de portafolio.
