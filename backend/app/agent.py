import operator
from typing import TypedDict, Annotated, List, Any
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.constants import END

# --- MODIFICATION: Import the new re-ranking tool instead of the old one ---
from .tools.rag_tool_rerank import RerankRetrieveTool

# AgentState definition remains the same
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str

class Agent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        
        # --- MODIFICATION: Instantiate the new tool ---
        # The agent is now equipped with the more advanced tool.
        tools = [RerankRetrieveTool()]
        self.tools_map = {tool.name: tool for tool in tools}
        
        self.llm_with_tools = self.llm.bind_tools(tools)
        
        self.graph = self._build_graph()

    # The rest of the Agent class (_build_graph, _should_continue, _call_model, _call_tools)
    # remains exactly the same. No changes are needed there.

    def _build_graph(self):
        """Builds the LangGraph agent workflow."""
        workflow = StateGraph(AgentState)

        workflow.add_node("call_model", self._call_model)
        workflow.add_node("call_tools", self._call_tools)

        workflow.add_edge(START, "call_model")
        workflow.add_conditional_edges(
            "call_model",
            self._should_continue,
            {"continue": "call_tools", "__end__": END}
        )
        workflow.add_edge("call_tools", "call_model")

        return workflow.compile()

    def _should_continue(self, state: AgentState) -> str:
        """Determines the next step after the LLM call."""
        last_message = state["messages"][-1]
        return "continue" if isinstance(last_message, AIMessage) and last_message.tool_calls else "__end__"

    async def _call_model(self, state: AgentState) -> dict[str, Any]:
        """Invokes the LLM with the current message history."""
        messages = state["messages"]
        response = await self.llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def _call_tools(self, state: AgentState) -> dict[str, Any]:
        """
        Executes tools based on the LLM's request. It robustly injects
        the user_id from the state into the tool's execution context.
        """
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_to_call = self.tools_map.get(tool_name)

            if not tool_to_call:
                result_content = f"Error: Tool '{tool_name}' not found."
            else:
                try:
                    observation = await tool_to_call._arun(
                        query=tool_call["args"]["query"],
                        user_id=state["user_id"]
                    )
                    result_content = str(observation)
                except Exception as e:
                    result_content = f"Error executing tool {tool_name}: {e}"
            
            tool_results.append(
                ToolMessage(content=result_content, tool_call_id=tool_call["id"])
            )

        return {"messages": tool_results}