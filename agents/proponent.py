from langchain_cohere import ChatCohere
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse.langchain import CallbackHandler
from mcp_client.client import MCPClient
from a2a.protocol import A2AMessage
import os

PROPONENT_SYSTEM = """You are the Proponent in a formal debate.
Your role is to argue STRONGLY IN FAVOR of the given topic.
Rules:
- Make 2-3 clear, logical arguments per round
- Use evidence from your search tool to back claims
- When given an opponent's argument, directly rebut each point
- Be persuasive but factual — no logical fallacies
- Format: numbered points, each under 80 words
- End with a one-sentence summary of your strongest claim"""

class ProponentAgent:
    def __init__(self, mcp: MCPClient):
        self.llm = ChatCohere(
            model="command-a-03-2025",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )
        self.mcp = mcp

    async def argue(self, topic: str, round_num: int,
                    opponent_msg: A2AMessage | None, langfuse_handler) -> A2AMessage:
        # Search for evidence first
        evidence = await self.mcp.call_tool("search_tool",
            {"query": f"arguments in favor of {topic}"})
        evidence_text = "\n".join([e["content"] for e in evidence[:3]])

        prompt = f"""Topic: "{topic}"
Round: {round_num}
Evidence available:\n{evidence_text}
"""
        if opponent_msg:
            prompt += f"\nOpponent's last argument to rebut:\n{opponent_msg.content}"
        else:
            prompt += "\nThis is your opening argument."

        messages = [
            SystemMessage(content=PROPONENT_SYSTEM),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages,
            config={"callbacks": [langfuse_handler]})

        return A2AMessage(
            sender="proponent", receiver="opponent",
            round_number=round_num, message_type="argument" if not opponent_msg else "rebuttal",
            content=response.content,
            evidence=[e["url"] for e in evidence[:3]]
        )