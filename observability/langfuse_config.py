"""
Langfuse observability helpers — Python SDK v4.

Key v4 changes vs v2/v3:
  - CallbackHandler.__init__ no longer accepts trace_name / session_id / tags.
    Use propagate_attributes() context manager around the LangChain call instead.
  - Scoring uses client.create_score(session_id=...) — no trace_id needed.
  - Always call client.flush() at the end of a request so spans are flushed
    before the response is sent (important for short-lived FastAPI handlers).

Docs: https://langfuse.com/docs/integrations/langchain
Migration guide: https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4
"""
import contextlib
from typing import Generator

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

# Single shared client — reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY /
# LANGFUSE_HOST from the environment (set by run.sh via set -a + .env).
_client = get_client()


def get_trace_handler(topic: str, session_id: str) -> tuple[CallbackHandler, contextlib.AbstractContextManager]:
    """
    Return a (handler, ctx) pair.

    The caller MUST enter `ctx` as a context manager before invoking the
    LangGraph graph so that propagate_attributes() attaches trace_name,
    session_id, and tags to every span created inside the graph.

    Usage in api/main.py:
        handler, trace_ctx = get_trace_handler(topic, session_id)
        with trace_ctx:
            result = await graph.ainvoke(state, config={"callbacks": [handler]})
    """
    ctx = propagate_attributes(
        trace_name=f"debate:{topic[:40]}",
        session_id=session_id,
        tags=["debate-agent"],
        # metadata values must be dict[str, str] in v4
        metadata={"topic": topic[:200]},
    )
    handler = CallbackHandler()
    return handler, ctx


def score_debate(
    session_id: str,
    winner: str,
    proponent_score: int,
    opponent_score: int,
) -> None:
    """
    Log post-debate quality scores to Langfuse.

    Uses create_score(session_id=...) so we don't need an explicit trace_id
    — all traces tagged with this session_id will receive the scores.
    Calls flush() so the scores reach Langfuse before the response is returned.
    """
    _client.create_score(name="proponent_score", value=float(proponent_score), session_id=session_id)
    _client.create_score(name="opponent_score",  value=float(opponent_score),  session_id=session_id)
    _client.create_score(
        name="winner",
        value=1.0 if winner == "proponent" else 0.0,
        session_id=session_id,
        comment=f"Winner: {winner}",
    )
    _client.flush()