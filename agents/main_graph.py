import os
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

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
    Takes exact numbers from SQL, predictions from Time-Series, and historical context from Vector RAG.
    Combines these inputs into a cohesive, conversational, and highly accurate natural language response.
    """
    query = state.get("user_query", "")
    sql_data = state.get("sql_data", {})
    forecast_data = state.get("forecast_data", {})
    rag_context = state.get("rag_context", "")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
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
    """
    
    # Mocking execution if API key is missing
    if not os.environ.get("OPENAI_API_KEY"):
        final_answer = f"[MOCK RESPONSE]\nBased on the data:\nSQL: {sql_data}\nForecast: {forecast_data}\nContext: {rag_context}\n(This is a mock response because OPENAI_API_KEY is not set)."
        message = AIMessage(content=final_answer)
    else:
        message = llm.invoke([{"role": "system", "content": system_prompt}])
        
    return {"messages": [message]}

def build_graph():
    """
    Constructs the LangGraph workflow.
    """
    # Initialize the graph with our state
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("master_router", master_router_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("time_series_agent", time_series_agent_node)
    workflow.add_node("vector_rag_agent", vector_rag_agent_node)
    workflow.add_node("synthesis_agent", synthesis_agent_node)
    
    # Define edges
    # The workflow starts at the router
    workflow.set_entry_point("master_router")
    
    # The router fans out to the specific data-fetching agents
    # In a fully dynamic setup, we'd use conditional edges based on 'routing_decision'.
    # Here, we route to all of them, and they internally check if they should run or skip.
    workflow.add_edge("master_router", "sql_agent")
    workflow.add_edge("master_router", "time_series_agent")
    workflow.add_edge("master_router", "vector_rag_agent")
    
    # After data fetching, they all fan in to the synthesis agent
    workflow.add_edge("sql_agent", "synthesis_agent")
    workflow.add_edge("time_series_agent", "synthesis_agent")
    workflow.add_edge("vector_rag_agent", "synthesis_agent")
    
    # Synthesis ends the process
    workflow.add_edge("synthesis_agent", END)
    
    # Compile
    app = workflow.compile()
    return app

def run_query(query: str):
    """
    Entry point to run a user query through the compiled LangGraph.
    """
    app = build_graph()
    
    print(f"--- Processing Query: '{query}' ---")
    
    initial_state = {
        "user_query": query,
        "messages": [],
        "routing_decision": "",
        "sql_data": {},
        "forecast_data": {},
        "rag_context": ""
    }
    
    # Run the graph
    result = app.invoke(initial_state)
    
    print("\n--- Final Answer ---")
    print(result["messages"][-1].content)
    return result

if __name__ == "__main__":
    # Example usage
    sample_query = "Why did our server traffic drop last Tuesday, and what is the forecast for next week?"
    run_query(sample_query)
