from fastmcp import FastMCP
from tavily import TavilyClient
import cohere, os

mcp = FastMCP("debate-tools")
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
co = cohere.Client(os.getenv("COHERE_API_KEY"))

@mcp.tool()
def search_tool(query: str) -> list[dict]:
    """Search the web for evidence to support a debate argument."""
    results = tavily.search(query, max_results=5)
    return [{"url": r["url"], "content": r["content"]} for r in results["results"]]

@mcp.tool()
def fact_check_tool(claim: str, documents: list[str]) -> dict:
    """Rerank documents by relevance to a claim using Cohere Rerank."""
    response = co.rerank(
        model="rerank-english-v3.0",
        query=claim,
        documents=documents,
        top_n=3
    )
    return {"top_docs": [r.document["text"] for r in response.results]}

@mcp.tool()
def summarizer_tool(text: str, max_tokens: int = 200) -> str:
    """Summarize a long argument or evidence block."""
    response = co.chat(
        model="command-a-03-2025",
        message=f"Summarize this concisely in under {max_tokens} tokens:\n\n{text}"
    )
    return response.text

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)