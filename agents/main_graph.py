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
    
    # Format sql_data nicely
    formatted_data = []
    if isinstance(sql_data, list):
        # Group by metric name and get latest values
        metrics_dict = {}
        for item in sql_data[:20]:
            if isinstance(item, dict):
                metric_name = item.get('metric_name', 'Unknown')
                metric_value = item.get('metric_value', 0)
                timestamp = item.get('timestamp', '')
                
                # Only include price data, not volume for cleaner display
                if '_VOL' not in metric_name:
                    if metric_name not in metrics_dict:
                        metrics_dict[metric_name] = []
                    metrics_dict[metric_name].append({
                        'value': metric_value,
                        'timestamp': str(timestamp)[:10]  # Just date
                    })
        
        # Format as readable markdown
        for metric, values in sorted(metrics_dict.items()):
            if values:
                latest = values[0]
                formatted_data.append(f"- **{metric}**: ${latest['value']:.2f} (as of {latest['timestamp']})")
    
    data_section = "\n".join(formatted_data) if formatted_data else "No price data available"
    
    # Format forecast nicely
    forecast_section = ""
    if forecast_data and "predictions" in forecast_data:
        preds = forecast_data["predictions"]
        forecast_section = "**7-Day Price Forecast:**\n"
        for i, pred in enumerate(preds, 1):
            forecast_section += f"- Day {i}: ${pred:,.2f}\n"
    else:
        forecast_section = "Forecast data unavailable"
    
    # Build a professional markdown response
    final_answer = f"""## Market Analysis Report

### 📊 Recent Closing Prices
{data_section}

### 📈 {forecast_section}

### 🔍 Market Insights
{rag_context if rag_context and rag_context != "skipped" else "No recent anomalies detected in the historical data."}

---
*Analysis based on real-time market data with ARIMA time-series forecasting*"""
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
        response = llm.invoke(f"""Provide a brief, professional market analysis based on this report:
{final_answer}

Keep it concise (2-3 sentences) and focus on actionable insights.""")
        message = AIMessage(content=response.content)
    except Exception as e:
        # Fallback if LLM fails - just return the structured data
        print(f"LLM synthesis failed: {e}")
        message = AIMessage(content=final_answer)
            
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
