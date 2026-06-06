import os
import json
import pandas as pd
from typing import TypedDict, Annotated, Sequence
from operator import itemgetter
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Mock path for TimeSeriesModelingHub
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.time_series_hub import TimeSeriesModelingHub

# Define the State for LangGraph
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    user_query: str
    routing_decision: str
    sql_data: dict
    forecast_data: dict
    rag_context: str

# 1. Master Router Agent
def master_router_node(state: AgentState):
    """
    Analyzes the user's prompt and routes the task to the appropriate sub-agents.
    """
    query = state.get("user_query", "")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    
    prompt = f"""
    Analyze the following user query about time-series data. 
    Determine which of these agents need to be invoked to answer the query:
    - SQL: If the user asks for exact historical numerical data.
    - FORECAST: If the user asks for future predictions.
    - RAG: If the user asks for context, explanations of anomalies, or reasons for past drops/spikes.
    
    Query: "{query}"
    
    Return a JSON list of the required agents. Example: ["SQL", "FORECAST", "RAG"]
    """
    
    if not os.environ.get("GOOGLE_API_KEY"):
        decision_list = ["SQL", "FORECAST", "RAG"]
    else:
        try:
            response = llm.invoke(prompt)
            # Clean up markdown formatting if Gemini returns it
            content = response.content.replace('```json', '').replace('```', '').strip()
            decision_list = json.loads(content)
        except Exception as e:
            print(f"Router error: {e}")
            decision_list = ["SQL", "FORECAST", "RAG"]
            
    return {"routing_decision": ",".join(decision_list)}

# 2. SQL Database Agent
def sql_agent_node(state: AgentState):
    """
    Writes and executes safe SQL queries against the dbt mart tables to retrieve exact numbers.
    """
    decision = state.get("routing_decision", "")
    if "SQL" not in decision:
        return {"sql_data": {"status": "skipped"}}
        
    query = state.get("user_query", "")
    
    # Normally, an LLM generates the SQL based on schema.
    # Here we simulate fetching the exact numbers.
    engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
    
    try:
        df = pd.read_sql("SELECT * FROM marts.mart_time_series_features ORDER BY metric_hour DESC LIMIT 5", engine)
        data_dict = df.to_dict(orient="records")
    except Exception as e:
        data_dict = {"error": str(e)}
        
    return {"sql_data": data_dict}

# 3. Time-Series Agent
def time_series_agent_node(state: AgentState):
    """
    Dynamically calls the ARIMA or XGBoost functions to generate a live forecast.
    """
    decision = state.get("routing_decision", "")
    if "FORECAST" not in decision:
        return {"forecast_data": {"status": "skipped"}}
        
    try:
        engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
        df = pd.read_sql("SELECT metric_hour, target_value FROM marts.mart_time_series_features WHERE metric_name = 'AAPL' ORDER BY metric_hour", engine)
        
        # Use baseline ARIMA for demonstration
        series = df['target_value'].values
        # If no data, mock it out so it doesn't crash before data ingestion
        if len(series) < 10:
            forecast_result = {"method": "ARIMA", "steps": 7, "predictions": [100, 101, 102, 103, 105, 104, 106]}
        else:
            forecast = TimeSeriesModelingHub.forecast_arima(series, steps=7, order=(1,0,0))
            forecast_result = {"method": "ARIMA", "steps": 7, "predictions": forecast.tolist()}
    except Exception as e:
        forecast_result = {"error": str(e)}
        
    return {"forecast_data": forecast_result}

# 4. Vector RAG Agent
def vector_rag_agent_node(state: AgentState):
    """
    Embeds query and performs a similarity search in pgvector.
    """
    decision = state.get("routing_decision", "")
    if "RAG" not in decision:
        return {"rag_context": "skipped"}
        
    query = state.get("user_query", "")
    
    try:
        if not os.environ.get("GOOGLE_API_KEY"):
            context = "Skipped vector search due to missing Google API key."
        else:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            query_vector = embeddings.embed_query(query)
            query_vector_str = str(query_vector)
            
            engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
            
            sql = f"""
                SELECT content, embedding <-> '{query_vector_str}' AS distance
                FROM embeddings.documents
                ORDER BY distance ASC
                LIMIT 3;
            """
            df = pd.read_sql(sql, engine)
            context = "\n".join(df['content'].tolist()) if not df.empty else "No historical anomalies found."
    except Exception as e:
        context = f"Error fetching RAG context: {e}"
        
    return {"rag_context": context}
