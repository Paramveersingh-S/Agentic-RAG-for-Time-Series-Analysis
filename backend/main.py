from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Add agents folder to path to import the LangGraph orchestrator
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))
from main_graph import run_query

app = FastAPI(title="Agentic RAG API")

# Allow CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    chart_data: dict | None = None
    forecast_data: dict | None = None

@app.post("/api/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    try:
        # Run the LangGraph workflow
        result = run_query(request.query)
        
        # Extract the final synthesized message
        final_message = result["messages"][-1].content
        
        # Extract the raw data for charts
        sql_data = result.get("sql_data", {})
        forecast_data = result.get("forecast_data", {})
        
        return QueryResponse(
            answer=final_message,
            chart_data=sql_data if isinstance(sql_data, list) else None,
            forecast_data=forecast_data if forecast_data.get("status") != "skipped" else None
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
