from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from a2a.protocol import A2AMessage

class DebateState(TypedDict):
    topic: str
    max_rounds: int
    current_round: int
    proponent_messages: Annotated[list[A2AMessage], operator.add]
    opponent_messages:  Annotated[list[A2AMessage], operator.add]
    judge_verdict: dict | None
    status: str   # "arguing" | "judging" | "done"

async def proponent_node(state: DebateState, agents, langfuse):
    last_opponent = state["opponent_messages"][-1] if state["opponent_messages"] else None
    msg = await agents["proponent"].argue(
        state["topic"], state["current_round"], last_opponent, langfuse
    )
    return {"proponent_messages": [msg]}

async def opponent_node(state: DebateState, agents, langfuse):
    last_proponent = state["proponent_messages"][-1]
    msg = await agents["opponent"].argue(
        state["topic"], state["current_round"], last_proponent, langfuse
    )
    return {"opponent_messages": [msg], "current_round": state["current_round"] + 1}

async def judge_node(state: DebateState, agents, langfuse):
    verdict = await agents["judge"].evaluate(
        state["topic"], state["proponent_messages"], state["opponent_messages"], langfuse
    )
    return {"judge_verdict": verdict, "status": "done"}

def should_continue(state: DebateState) -> str:
    if state["current_round"] > state["max_rounds"]:
        return "judge"
    return "proponent"

def build_debate_graph(agents, langfuse):
    from functools import partial
    graph = StateGraph(DebateState)

    graph.add_node("proponent", partial(proponent_node, agents=agents, langfuse=langfuse))
    graph.add_node("opponent",  partial(opponent_node,  agents=agents, langfuse=langfuse))
    graph.add_node("judge",     partial(judge_node,     agents=agents, langfuse=langfuse))

    graph.set_entry_point("proponent")
    graph.add_edge("proponent", "opponent")
    graph.add_conditional_edges("opponent", should_continue,
        {"proponent": "proponent", "judge": "judge"})
    graph.add_edge("judge", END)

    return graph.compile()