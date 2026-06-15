"""LangGraph wiring: router -> retrieve -> generate -> grounding (-> fallback loop).

Skeleton in P3-T1: nodes are placeholders so the graph compiles and runs end to
end. Subsequent tasks (P3-T2..T6) replace each placeholder with real logic.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from repo_expert.agent.llm import chat, chat_json
from repo_expert.agent.state import AgentState
from repo_expert.config.instance import get_instance_config
from repo_expert.retrieval.models import RetrievalResult
from repo_expert.retrieval.registry import available_sources, get_retrievers

MAX_ATTEMPTS = 2

_SOURCE_DESCRIPTIONS = {
    "kb": "Project documentation and source code (how things work / how X is implemented).",
    "issues": "Live GitHub issues and pull requests (known bugs, feature status, is-this-broken).",
}

_ROUTER_SYSTEM = (
    "You route a developer's question to knowledge sources. Choose the minimal set "
    "of sources that can answer it. Reply as JSON: {\"route\": [\"<source>\", ...]}. "
    "Use 'issues' for questions about bugs, regressions, or whether something is "
    "known/open; use 'kb' for how-to and how-is-X-implemented questions; use both "
    "when the question spans current status and implementation."
)


# --- Nodes ---------------------------------------------------------------------

def router_node(state: AgentState) -> AgentState:
    sources = available_sources(get_instance_config())
    if len(sources) == 1:
        return {"route": sources}
    catalog = "\n".join(f"- {s}: {_SOURCE_DESCRIPTIONS.get(s, s)}" for s in sources)
    data = chat_json(
        _ROUTER_SYSTEM,
        f"Available sources:\n{catalog}\n\nQuestion: {state['question']}",
    )
    route = [s for s in data.get("route", []) if s in sources]
    return {"route": route or ["kb"]}


def retrieve_node(state: AgentState) -> AgentState:
    retrievers = get_retrievers(get_instance_config())
    results = []
    for name in state.get("route", ["kb"]):
        retriever = retrievers.get(name)
        if retriever:
            results.extend(retriever(state["question"], top=6))
    return {"results": results}


_CONTEXT_LIMIT = 8
_SNIPPET_CHARS = 900

_GENERATE_SYSTEM = (
    "You are a precise codebase assistant. Answer the question using ONLY the "
    "numbered sources. Cite the sources you use inline as [n]. If the sources do "
    "not contain the answer, say you don't know. Be concise and technical."
)

_GROUNDING_SYSTEM = (
    "You verify whether an answer is fully supported by the provided sources. "
    "Reply as JSON {\"grounded\": true|false, \"reason\": \"...\"}. Mark false if the "
    "answer makes any claim not backed by the sources."
)


def _format_sources(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results[:_CONTEXT_LIMIT], start=1):
        c = r.citation
        loc = c.file_path or "/".join(c.section_path) or c.url
        lines.append(f"[{i}] ({r.kind}) {c.title} — {loc}\n{r.content[:_SNIPPET_CHARS]}")
    return "\n\n".join(lines)


def generate_node(state: AgentState) -> AgentState:
    results = state.get("results", [])
    if not results:
        return {"draft": "", "answer": "I don't know — no relevant sources found.", "citations": []}
    sources = _format_sources(results)
    scope = get_instance_config().scope_prompt
    system = f"{_GENERATE_SYSTEM}\n\n{scope}" if scope else _GENERATE_SYSTEM
    answer = chat(
        system,
        f"Sources:\n{sources}\n\nQuestion: {state['question']}",
    )
    citations = [r.citation for r in results[:_CONTEXT_LIMIT]]
    return {"draft": answer, "answer": answer, "citations": citations}


def grounding_node(state: AgentState) -> AgentState:
    draft = state.get("draft", "")
    results = state.get("results", [])
    if not draft or not results:
        return {"grounded": False}
    sources = _format_sources(results)
    data = chat_json(
        _GROUNDING_SYSTEM,
        f"Sources:\n{sources}\n\nAnswer: {draft}",
    )
    return {"grounded": bool(data.get("grounded", False))}


def fallback_node(state: AgentState) -> AgentState:
    """On a weak/ungrounded answer, widen the route to all available sources."""
    all_sources = available_sources(get_instance_config())
    current = set(state.get("route", []))
    widened = [s for s in all_sources if s not in current] or list(all_sources)
    new_route = list(dict.fromkeys([*state.get("route", []), *widened]))
    return {
        "route": new_route,
        "attempts": state.get("attempts", 0) + 1,
        "fallback_used": True,
    }


# --- Edge logic ----------------------------------------------------------------

def _after_grounding(state: AgentState) -> str:
    """End if the draft is grounded or we've exhausted attempts; else revise."""
    if state.get("grounded") or state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "end"
    return "revise"


def build_graph():
    """Compile and return the agent graph."""
    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("grounding", grounding_node)
    g.add_node("fallback", fallback_node)

    g.add_edge(START, "router")
    g.add_edge("router", "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "grounding")
    g.add_conditional_edges("grounding", _after_grounding, {"end": END, "revise": "fallback"})
    g.add_edge("fallback", "retrieve")

    return g.compile()
