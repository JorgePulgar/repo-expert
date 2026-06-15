"""LangGraph wiring: router -> retrieve -> generate -> grounding (-> fallback loop).

Skeleton in P3-T1: nodes are placeholders so the graph compiles and runs end to
end. Subsequent tasks (P3-T2..T6) replace each placeholder with real logic.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from repo_expert.agent.state import AgentState

MAX_ATTEMPTS = 2


# --- Placeholder nodes (filled in later tasks) ---------------------------------

def router_node(state: AgentState) -> AgentState:
    return {"route": ["kb"]}


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
