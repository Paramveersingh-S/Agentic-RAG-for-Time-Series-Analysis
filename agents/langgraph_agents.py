import os
import json
import pandas as pd
from typing import TypedDict, Annotated, Sequence
from operator import itemgetter
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sqlalchemy import create_engine

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
    In a real implementation, this would use an LLM with tool calling or structured output
    to decide which agents need to be invoked.
    """
    query = state.get("user_query", "")
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = f"""
    Analyze the following user query about time-series data. 
    Determine which of these agents need to be invoked to answer the query:
    - SQL: If the user asks for exact historical numerical data.
    - FORECAST: If the user asks for future predictions.
    - RAG: If the user asks for context, explanations of anomalies, or reasons for past drops/spikes.
    
    Query: "{query}"
    
    Return a JSON list of the required agents. Example: ["SQL", "FORECAST", "RAG"]
    """
    
    # Mocking the decision for demonstration if API key is not set
    if not os.environ.get("OPENAI_API_KEY"):
        decision_list = ["SQL", "FORECAST", "RAG"]
    else:
        response = llm.invoke(prompt)
        try:
            decision_list = json.loads(response.content)
        except:
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
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    # Normally, an LLM generates the SQL based on schema.
    # Here we simulate fetching the exact numbers for a metric.
    engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
    
    try:
        # Mocking safe SQL execution for safety. 
        # In a real setup, we'd use langchain.utilities.SQLDatabase
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
        
    # Simulate fetching historical data
    try:
        engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
        df = pd.read_sql("SELECT metric_hour, target_value FROM marts.mart_time_series_features WHERE metric_name = 'server_requests' ORDER BY metric_hour", engine)
        
        # Use baseline ARIMA for demonstration
        series = df['target_value'].values
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
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        query_vector = embeddings.embed_query(query)
        query_vector_str = str(query_vector)
        
        engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
        
        # Perform similarity search using pgvector's <-> operator (L2 distance)
        sql = f"""
            SELECT content, embedding <-> '{query_vector_str}' AS distance
            FROM embeddings.documents
            ORDER BY distance ASC
            LIMIT 3;
        """
        df = pd.read_sql(sql, engine)
        context = "\n".join(df['content'].tolist())
    except Exception as e:
        context = f"Error fetching RAG context: {e}"
        
    return {"rag_context": context}
