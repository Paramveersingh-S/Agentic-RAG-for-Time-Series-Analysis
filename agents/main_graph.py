import os
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import nodes and state from our agents module
from langgraph_agents import (
    AgentState, 
    master_router_node, 
    sql_agent_node, 
    time_series_agent_node, 
    vector_rag_agent_node
)

# 5. Synthesis Agent
def synthesis_agent_node(state: AgentState):
    """
    Combines these inputs into a cohesive, conversational natural language response.
    """
    query = state.get("user_query", "")
    sql_data = state.get("sql_data", {})
    forecast_data = state.get("forecast_data", {})
    rag_context = state.get("rag_context", "")
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    
    system_prompt = f"""
    You are an expert Data Engineer and AI Architect. A user has asked the following question about their time-series data:
    "{query}"
    
    You have been provided with data gathered from specialized sub-agents:
    
    1. SQL Database Data (Exact Numbers):
    {sql_data}
    
    2. Time-Series Forecast Data (Predictions):
    {forecast_data}
    
    3. Historical Context (Vector RAG / Anomaly Explanations):
    {rag_context}
    
    Combine these inputs into a cohesive, conversational, and highly accurate natural language response.
    If an agent returned "skipped" or empty data, simply ignore that aspect. 
    Explain the anomalies based on the RAG context, provide the hard numbers from the SQL data, and discuss future trends using the forecast data.
    Format your response cleanly using markdown (e.g., bolding numbers).
    """
    
    if not os.environ.get("GOOGLE_API_KEY"):
        final_answer = f"[MOCK RESPONSE]\nBased on the data:\nSQL: {sql_data}\nForecast: {forecast_data}\nContext: {rag_context}\n(This is a mock response because GOOGLE_API_KEY is not set)."
        message = AIMessage(content=final_answer)
    else:
        try:
            # Gemini chat doesn't use the 'system' role in the same way OpenAI does by default in basic invoke,
            # but Langchain handles message conversion. For robust Gemini prompting, we can just send it as a Human message.
            response = llm.invoke(system_prompt)
            message = AIMessage(content=response.content)
        except Exception as e:
            message = AIMessage(content=f"Error generating synthesis: {e}")
            
    return {"messages": [message]}

def router_logic(state: AgentState):
    decision = state.get("routing_decision", "")
    targets = []
    if "SQL" in decision: targets.append("sql_agent")
    if "FORECAST" in decision: targets.append("time_series_agent")
    if "RAG" in decision: targets.append("vector_rag_agent")
    return targets if targets else ["synthesis_agent"]

def build_graph():
    """
    Constructs the LangGraph workflow.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("master_router", master_router_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("time_series_agent", time_series_agent_node)
    workflow.add_node("vector_rag_agent", vector_rag_agent_node)
    workflow.add_node("synthesis_agent", synthesis_agent_node)
    
    workflow.set_entry_point("master_router")
    
    # Use dynamic conditional edge to branch in parallel
    workflow.add_conditional_edges("master_router", router_logic)
    
    workflow.add_edge("sql_agent", "synthesis_agent")
    workflow.add_edge("time_series_agent", "synthesis_agent")
    workflow.add_edge("vector_rag_agent", "synthesis_agent")
    
    workflow.add_edge("synthesis_agent", END)
    
    app = workflow.compile()
    return app

def run_query(query: str):
    app = build_graph()
    
    initial_state = {
        "user_query": query,
        "messages": [],
        "routing_decision": "",
        "sql_data": {},
        "forecast_data": {},
        "rag_context": ""
    }
    
    result = app.invoke(initial_state)
    return result

if __name__ == "__main__":
    sample_query = "Why did AAPL drop last month, and what is the forecast?"
    result = run_query(sample_query)
    print("\n--- Final Answer ---")
    print(result["messages"][-1].content)
