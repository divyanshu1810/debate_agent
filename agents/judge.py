from langchain_cohere import ChatCohere
from langchain_core.messages import SystemMessage, HumanMessage
from mcp_client.client import MCPClient
from a2a.protocol import A2AMessage
import os, json, re

JUDGE_SYSTEM = """You are an impartial debate judge.
Evaluate the full debate transcript and score each side.

Scoring criteria (10 points each):
1. Argument strength — clarity, logic, structure
2. Evidence quality — factual backing, source credibility
3. Rebuttal effectiveness — how well they countered the opponent
4. Persuasiveness — overall impact

Output format (strict JSON, no markdown fences):
{
  "proponent_scores": {"argument_strength": X, "evidence_quality": X, "rebuttal": X, "persuasiveness": X},
  "opponent_scores": {"argument_strength": X, "evidence_quality": X, "rebuttal": X, "persuasiveness": X},
  "proponent_total": X,
  "opponent_total": X,
  "winner": "proponent" | "opponent" | "draw",
  "reasoning": "2-3 sentence explanation",
  "key_turning_point": "which argument/round decided it"
}"""


class JudgeAgent:
    def __init__(self, mcp: MCPClient):
        self.llm = ChatCohere(
            model="command-a-03-2025",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )
        self.mcp = mcp

    async def evaluate(
        self,
        topic: str,
        proponent_messages: list[A2AMessage],
        opponent_messages: list[A2AMessage],
        langfuse_handler
    ) -> dict:
        # Build a readable transcript
        transcript_lines = []
        for i, (p, o) in enumerate(zip(proponent_messages, opponent_messages), 1):
            transcript_lines.append(f"--- Round {i} ---")
            transcript_lines.append(f"PROPONENT:\n{p.content}\n")
            transcript_lines.append(f"OPPONENT:\n{o.content}\n")

        # Handle unequal lengths (last proponent arg may have no opponent reply)
        if len(proponent_messages) > len(opponent_messages):
            i = len(opponent_messages) + 1
            transcript_lines.append(f"--- Round {i} ---")
            transcript_lines.append(f"PROPONENT:\n{proponent_messages[-1].content}\n")
            transcript_lines.append("OPPONENT: (no response — debate ended)\n")

        transcript = "\n".join(transcript_lines)

        prompt = f"""Topic: "{topic}"

Full debate transcript:
{transcript}

Evaluate the debate and return your verdict as strict JSON (no markdown)."""

        messages = [
            SystemMessage(content=JUDGE_SYSTEM),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages,
            config={"callbacks": [langfuse_handler]})

        return _parse_json_verdict(response.content)


def _parse_json_verdict(text: str) -> dict:
    """Extract and parse the JSON verdict, stripping markdown code fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)