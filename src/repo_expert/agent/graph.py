"""LangGraph wiring: router -> retrieve -> generate -> grounding (-> fallback loop).

Skeleton in P3-T1: nodes are placeholders so the graph compiles and runs end to
end. Subsequent tasks (P3-T2..T6) replace each placeholder with real logic.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from repo_expert.agent.llm import chat_json
from repo_expert.agent.state import AgentState
from repo_expert.config.instance import get_instance_config
from repo_expert.retrieval.registry import available_sources

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
    return {"results": []}


def generate_node(state: AgentState) -> AgentState:
    return {"draft": "", "answer": "", "citations": []}


def grounding_node(state: AgentState) -> AgentState:
    return {"grounded": True}


def fallback_node(state: AgentState) -> AgentState:
    return {"attempts": state.get("attempts", 0) + 1, "fallback_used": True}


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
