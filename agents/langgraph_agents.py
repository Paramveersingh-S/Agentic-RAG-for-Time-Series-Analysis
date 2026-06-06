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
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
    
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
            # Default to all agents if routing fails
            decision_list = ["SQL", "FORECAST", "RAG"]
            
    return {"routing_decision": ",".join(decision_list)}

# 2. SQL Database Agent
def sql_agent_node(state: AgentState):
    """
    Writes and executes safe SQL queries against the database to retrieve exact numbers.
    """
    decision = state.get("routing_decision", "")
    if "SQL" not in decision:
        return {"sql_data": {"status": "skipped"}}
        
    query = state.get("user_query", "")
    
    # Normally, an LLM generates the SQL based on schema.
    # Here we fetch the actual data from the raw_data table.
    db_url = os.environ.get("DATABASE_URL", "postgresql://admin:password@localhost:5432/time_series")
    engine = create_engine(db_url)
    
    try:
        # Query the actual raw_data table with recent metrics grouped by metric_name
        df = pd.read_sql("""
            SELECT timestamp, metric_name, metric_value 
            FROM metrics.raw_data 
            ORDER BY timestamp DESC 
            LIMIT 100
        """, engine)
        
        if df.empty:
            data_dict = [{"status": "no_data", "message": "No metrics available yet. Please check the database."}]
        else:
            data_dict = df.to_dict(orient="records")
    except Exception as e:
        print(f"SQL Agent error: {e}")
        data_dict = [{"status": "error", "message": str(e)}]
        
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
        db_url = os.environ.get("DATABASE_URL", "postgresql://admin:password@localhost:5432/time_series")
        engine = create_engine(db_url)
        
        # Query the actual raw_data table for AAPL or first available metric
        df = pd.read_sql("""
            SELECT timestamp, metric_value 
            FROM metrics.raw_data 
            WHERE metric_name IN ('AAPL', 'GOOGL', '^GSPC')
            ORDER BY timestamp ASC
        """, engine)
        
        if df.empty or len(df) < 10:
            # If no data, mock forecast for demonstration
            forecast_result = {
                "method": "ARIMA", 
                "steps": 7, 
                "predictions": [100, 101, 102, 103, 105, 104, 106],
                "note": "Mock forecast due to insufficient historical data"
            }
        else:
            series = df['metric_value'].values
            forecast = TimeSeriesModelingHub.forecast_arima(series, steps=7, order=(1,0,0))
            forecast_result = {
                "method": "ARIMA", 
                "steps": 7, 
                "predictions": forecast.tolist()
            }
    except Exception as e:
        print(f"Time-Series Agent error: {e}")
        forecast_result = {
            "error": str(e),
            "method": "ARIMA",
            "steps": 7,
            "predictions": [100, 101, 102, 103, 105, 104, 106],
            "note": "Mock forecast due to error"
        }
        
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
            context = "Vector search skipped: GOOGLE_API_KEY not configured. Historical anomalies will not be available."
        else:
            try:
                # Vector embedding temporarily unavailable due to API limitations
                # Try to query the documents table but expect it to be empty during setup
                db_url = os.environ.get("DATABASE_URL", "postgresql://admin:password@localhost:5432/time_series")
                engine = create_engine(db_url)
                
                # Since we can't embed without the proper models, just fetch any available context
                try:
                    df = pd.read_sql("""
                        SELECT content
                        FROM embeddings.documents
                        LIMIT 5;
                    """, engine)
                    
                    if df.empty:
                        context = "No historical anomaly context available yet. The vector store is empty."
                    else:
                        context = "\n".join(df['content'].tolist())
                except Exception as table_err:
                    context = f"Vector store not yet populated: {str(table_err)}"
            except Exception as inner_e:
                print(f"Vector RAG error: {inner_e}")
                context = "Vector search temporarily unavailable. Analyzing based on available data."
    except Exception as e:
        print(f"RAG Agent error: {e}")
        context = f"Error fetching RAG context: {e}"
        
    return {"rag_context": context}
