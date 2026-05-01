from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from safety.guard import scan_input, scan_output
from graph.debate_graph import build_debate_graph
from agents.proponent import ProponentAgent
from agents.opponent import OpponentAgent
from agents.judge import JudgeAgent
from mcp_client.client import MCPClient
from observability.langfuse_config import get_trace_handler, score_debate
import uuid

app = FastAPI(title="Debate Agent API")

class DebateRequest(BaseModel):
    topic: str
    max_rounds: int = 3

@app.post("/debate")
async def run_debate(req: DebateRequest):
    # Safety scan the input topic
    clean_topic, is_safe = scan_input(req.topic)
    if not is_safe:
        raise HTTPException(400, "Topic flagged by safety scanner")

    session_id = str(uuid.uuid4())

    # get_trace_handler returns (CallbackHandler, propagate_attributes ctx).
    # The `with trace_ctx:` block sets trace_name / session_id / tags on all
    # LangGraph spans via OpenTelemetry context propagation (Langfuse v4 API).
    langfuse_handler, trace_ctx = get_trace_handler(clean_topic, session_id)

    async with MCPClient("http://localhost:8001/mcp") as mcp:
        agents = {
            "proponent": ProponentAgent(mcp),
            "opponent":  OpponentAgent(mcp),
            "judge":     JudgeAgent(mcp)
        }
        graph = build_debate_graph(agents, langfuse_handler)

        with trace_ctx:
            result = await graph.ainvoke({
                "topic": clean_topic,
                "max_rounds": req.max_rounds,
                "current_round": 1,
                "proponent_messages": [],
                "opponent_messages": [],
                "judge_verdict": None,
                "status": "arguing"
            })

    verdict = result["judge_verdict"]
    score_debate(
        session_id,          # v4: score by session_id, not trace_id
        verdict["winner"],
        verdict["proponent_total"],
        verdict["opponent_total"]
    )

    return {
        "session_id": session_id,
        "topic": clean_topic,
        "rounds": req.max_rounds,
        "transcript": {
            "proponent": [m.dict() for m in result["proponent_messages"]],
            "opponent":  [m.dict() for m in result["opponent_messages"]]
        },
        "verdict": verdict
    }