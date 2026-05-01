from langchain_cohere import ChatCohere
from langchain_core.messages import SystemMessage, HumanMessage
from mcp_client.client import MCPClient
from a2a.protocol import A2AMessage
import os

OPPONENT_SYSTEM = """You are the Opponent in a formal debate.
Your role is to argue STRONGLY AGAINST the given topic.
Rules:
- Counter every point the proponent makes with direct refutation
- Use evidence from your search tool to undermine their claims
- Raise 2-3 original counter-arguments per round
- Point out logical weaknesses or missing context in their arguments
- Format: numbered points, each under 80 words
- End with a one-sentence summary of why the topic's premise fails"""


class OpponentAgent:
    def __init__(self, mcp: MCPClient):
        self.llm = ChatCohere(
            model="command-a-03-2025",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )
        self.mcp = mcp

    async def argue(
        self,
        topic: str,
        round_num: int,
        proponent_msg: A2AMessage,
        langfuse_handler
    ) -> A2AMessage:
        # Search for counter-evidence
        evidence = await self.mcp.call_tool("search_tool",
            {"query": f"arguments against {topic}"})
        evidence_text = "\n".join([e["content"] for e in evidence[:3]])

        prompt = f"""Topic: "{topic}"
Round: {round_num}
Evidence available:\n{evidence_text}

Proponent's argument to rebut:
{proponent_msg.content}"""

        messages = [
            SystemMessage(content=OPPONENT_SYSTEM),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages,
            config={"callbacks": [langfuse_handler]})

        return A2AMessage(
            sender="opponent", receiver="proponent",
            round_number=round_num, message_type="rebuttal",
            content=response.content,
            evidence=[e["url"] for e in evidence[:3]]
        )