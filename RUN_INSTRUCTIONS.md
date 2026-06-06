# 🚀 Agentic RAG Time-Series Analysis Platform - Run Instructions

This guide provides complete step-by-step instructions to set up and run the Agentic RAG Time-Series Analysis platform locally.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Troubleshooting](#troubleshooting)
5. [Architecture Overview](#architecture-overview)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12+** installed
- **Node.js 18+** and npm installed
- **Docker & Docker Compose** installed
- **PostgreSQL** (via Docker)
- **Google API Key** for Gemini models (optional but recommended)

### Check Installations

```bash
python --version      # Should be 3.12+
node --version       # Should be 18+
npm --version        # Should be 9+
docker --version     # Docker should be installed
docker-compose --version  # Docker Compose should be installed
```

---

## Quick Start

Get the application running in 5 minutes:

### Step 1: Navigate to Project Root
```bash
cd /workspaces/Agentic-RAG-for-Time-Series-Analysis
```

### Step 2: Set Up Environment Variables
Create a `.env` file in the root directory:

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://admin:password@localhost:5432/time_series
GOOGLE_API_KEY=your_google_api_key_here
EOF
```

**Note:** If you don't have a Google API key, the system will still work with reduced functionality (no embeddings).

### Step 3: Start Docker Services (PostgreSQL)
```bash
docker-compose up -d
```

Verify PostgreSQL is running:
```bash
docker ps | grep time_series_db
```

### Step 4: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Seed the Database
Populate the database with 30 days of real stock market data:

```bash
python seed_data.py
```

**Output should show:**
```
Connecting to PostgreSQL...
Fetching 30 days of data for AAPL...
Fetching 30 days of data for GOOGL...
Fetching 30 days of data for ^GSPC...
Inserting 132 records into the database...
✅ Database successfully seeded with real data!
```

### Step 6: Seed the Vector Store
Populate the vector store with market insights and anomaly context:

```bash
python seed_vectors.py
```

**Output should show:**
```
Connecting to PostgreSQL...
Seeding 8 documents into vector store...
✅ Vector store successfully seeded with market insights!
   Total documents in vector store: 8
```

### Step 7: Install Frontend Dependencies
```bash
cd frontend
npm install
```

### Step 8: Start the Backend Server
Open a new terminal and run:

```bash
cd /workspaces/Agentic-RAG-for-Time-Series-Analysis
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Output should show:**
```
INFO:     Will watch for changes in these directories: ['/workspaces/Agentic-RAG-for-Time-Series-Analysis']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process using WatchFiles
```

### Step 9: Start the Frontend Server
Open another terminal and run:

```bash
cd /workspaces/Agentic-RAG-for-Time-Series-Analysis/frontend
npm run dev
```

**Output should show:**
```
  VITE v8.0.16  ready in 306 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Step 10: Access the Application
Open your browser and visit: **http://localhost:5173**

---

## Detailed Setup

### Directory Structure

```
Agentic-RAG-for-Time-Series-Analysis/
├── .env                          # Environment variables
├── docker-compose.yml            # Docker services definition
├── requirements.txt              # Python dependencies
├── seed_data.py                  # Script to seed financial data
├── seed_vectors.py               # Script to seed vector store
│
├── backend/
│   └── main.py                   # FastAPI REST API
│
├── frontend/
│   ├── package.json              # Node.js dependencies
│   ├── vite.config.js            # Vite bundler config
│   ├── index.html                # HTML entry point
│   └── src/
│       ├── App.jsx               # Main React component
│       ├── App.css               # Styling
│       └── main.jsx              # React DOM render
│
├── agents/
│   ├── langgraph_agents.py       # Individual agent implementations
│   └── main_graph.py             # LangGraph workflow orchestration
│
├── models/
│   └── time_series_hub.py        # Time-series forecasting models (ARIMA, XGBoost)
│
├── init/
│   └── init.sql                  # Database schema initialization
│
├── dbt/                          # Data transformation (optional)
├── airflow/                      # Workflow orchestration (optional)
└── RUN_INSTRUCTIONS.md           # This file
```

### Database Schema

The application uses two PostgreSQL schemas:

#### 1. `metrics` Schema - Time-Series Data
```sql
-- Raw time-series metrics
CREATE TABLE metrics.raw_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(255) NOT NULL,    -- 'AAPL', 'GOOGL', '^GSPC', etc.
    metric_value DOUBLE PRECISION NOT NULL,
    tags JSONB
);
```

**Sample data after seeding:**
- 30 days of daily stock prices for AAPL, GOOGL, ^GSPC
- Volume data for each metric
- Total: ~132 records

#### 2. `embeddings` Schema - Vector Store
```sql
-- Vector embeddings for RAG context
CREATE TABLE embeddings.documents (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source_type VARCHAR(50),    -- 'market_insight', 'anomaly_explanation', etc.
    content TEXT NOT NULL,      -- Original text content
    embedding VECTOR(1536)      -- Vector embedding (pgvector)
);
```

**Sample data after seeding:**
- 8 market insights for AAPL, GOOGL, ^GSPC
- 2 anomaly explanation templates
- 2 technical analysis guidelines
- 1 risk context document

---

## Architecture Overview

### System Components

```
User Query (Browser)
        ↓
  React Frontend (Port 5173)
        ↓
  FastAPI Backend (Port 8000)
        ↓
   LangGraph Orchestrator
     ├─→ Master Router Agent
     │     └─→ Routes to: SQL | FORECAST | RAG
     │
     ├─→ SQL Agent
     │     └─→ Queries metrics.raw_data table
     │
     ├─→ Time-Series Agent
     │     └─→ Generates ARIMA 7-day forecasts
     │
     └─→ RAG Agent
           └─→ Similarity search in embeddings.documents
     
     ↓ (All agents)
     
   Synthesis Agent
     └─→ Formats response + chart data
           ↓
   Response to Frontend
     ├─→ Markdown report
     ├─→ Chart data (historical prices)
     └─→ Forecast data (7-day predictions)
```

### Data Flow

1. **User enters query:** "Show me stock prices and forecasts"

2. **Master Router** analyzes query → decides to invoke: SQL, FORECAST, RAG agents

3. **SQL Agent:**
   - Executes: `SELECT * FROM metrics.raw_data ORDER BY timestamp DESC LIMIT 100`
   - Returns: Array of {timestamp, metric_name, metric_value} objects

4. **Time-Series Agent:**
   - Fits ARIMA(1,0,0) model to historical data
   - Generates 7-day forecast with predictions
   - Returns: {predictions: [3237.22, 2604.77, ...], forecast_std: [150.5, ...]}

5. **RAG Agent:**
   - Queries embeddings.documents for market context
   - Returns: Market insights + anomaly explanations

6. **Synthesis Agent:**
   - Combines all agent outputs
   - Formats as professional markdown report
   - Prepares data for frontend visualization

7. **Frontend:**
   - Displays markdown report with formatted prices
   - Renders interactive chart with historical + forecast lines
   - Shows three stock prices (AAPL, GOOGL, ^GSPC) with color coding

---

## Understanding the "Vector Store Empty" Issue

### Why This Message Appears

The message **"No historical anomaly context available yet. The vector store is empty."** appears when:

1. The `embeddings.documents` table has no data
2. The RAG agent cannot retrieve market insights or anomaly context
3. Users ask for explanations about price movements or anomalies

### Why We Populate It

The vector store provides:

- **Market Context:** Why stock prices move (Fed policy, earnings, sector trends)
- **Anomaly Explanations:** Reasons for price spikes or drops (supply chain, competition, regulations)
- **Technical Analysis:** Support levels, resistance, volatility patterns
- **Risk Context:** Systemic vs idiosyncratic risks affecting prices

### Solution: Run seed_vectors.py

This script:
1. Creates 8 diverse documents covering market insights
2. Generates 1536-dimensional embeddings (placeholder zeros for now)
3. Inserts into `embeddings.documents` table
4. RAG agent can now retrieve context for queries

**After seeding:**
- RAG agent finds relevant market insights
- Responses include "Why did the price move?" context
- Chat becomes more informative and contextual

---

## Running Individual Components

### Start Only Database
```bash
docker-compose up -d
```

### Start Only Backend
```bash
cd /workspaces/Agentic-RAG-for-Time-Series-Analysis
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Only Frontend
```bash
cd /workspaces/Agentic-RAG-for-Time-Series-Analysis/frontend
npm run dev
```

### Test Backend Health
```bash
curl -s http://localhost:8000/api/health | jq .
# Output: {"status":"ok"}
```

### Test Database Connection
```bash
psql postgresql://admin:password@localhost:5432/time_series
# Once connected:
SELECT COUNT(*) FROM metrics.raw_data;
SELECT COUNT(*) FROM embeddings.documents;
```

---

## Troubleshooting

### Issue: Database Connection Error

**Error:** `connection refused on localhost:5432`

**Solution:**
```bash
# Check if PostgreSQL container is running
docker ps | grep time_series_db

# If not running, start it
docker-compose up -d

# Verify it's healthy
docker logs time_series_db
```

### Issue: Module Not Found (Python)

**Error:** `ModuleNotFoundError: No module named 'langchain'`

**Solution:**
```bash
pip install -r requirements.txt
# Or specific module:
pip install langchain langchain-google-genai
```

### Issue: Node Modules Missing (Frontend)

**Error:** `npm: command not found` or module errors

**Solution:**
```bash
cd frontend
npm install
npm run dev
```

### Issue: Port Already in Use

**Error:** `Address already in use` on port 8000 or 5173

**Solution - for port 8000:**
```bash
# Find process using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
```

**Solution - for port 5173:**
```bash
# Use a different port
cd frontend
npm run dev -- --port 5174
```

### Issue: Chart Not Displaying

**Causes & Solutions:**
1. **Backend not running:** Start backend with `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2. **Database empty:** Run `python seed_data.py`
3. **CORS error:** Restart backend (CORS should be enabled)
4. **Browser cache:** Do a hard refresh (Ctrl+Shift+R)

### Issue: "No historical anomaly context available"

**Solution:**
```bash
# Seed the vector store
python seed_vectors.py
# Refresh browser
```

### Issue: Google API Key Error

**Error:** `models/gemini-1.5-flash is not found`

**Cause:** Provided API key doesn't support embeddings or the model

**Solution:** 
- Optional: Provide a working Google API key in `.env`
- System will gracefully fall back to Gemini-pro and disable embeddings
- All other features work normally

---

## Command Reference

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start PostgreSQL database |
| `python seed_data.py` | Load 30 days of stock data |
| `python seed_vectors.py` | Populate vector store with market insights |
| `python -m uvicorn backend.main:app --reload` | Start FastAPI backend |
| `cd frontend && npm run dev` | Start React frontend |
| `curl http://localhost:8000/api/health` | Check backend health |
| `cd frontend && npm run build` | Build frontend for production |

---

## API Reference

### Chat Endpoint

**POST** `/api/chat`

Request:
```json
{
  "query": "What are the latest stock prices?"
}
```

Response:
```json
{
  "answer": "## Market Analysis Report\n\n### 📊 Recent Closing Prices\n- **AAPL**: $307.34\n- **GOOGL**: $368.53\n- **^GSPC**: $7383.74",
  "chart_data": [
    {
      "timestamp": "2026-06-05T04:00:00Z",
      "metric_name": "AAPL",
      "metric_value": 307.34
    }
  ],
  "forecast_data": {
    "predictions": [3237.22, 2604.77, 2744.21, 2713.46, 2720.24, 2718.75, 2719.08]
  }
}
```

### Health Check Endpoint

**GET** `/api/health`

Response:
```json
{
  "status": "ok"
}
```

---

## Performance Tips

1. **Reduce Chart Data:** Limit to last 30 days for faster rendering
2. **Cache Responses:** Backend caches forecast calculations
3. **Optimize Vector Search:** Add index on embedding column (already done in init.sql)
4. **Use Production Build:** `npm run build` for frontend performance

---

## Next Steps

- ✅ Complete setup and verify all services running
- 📊 Submit sample queries to test the system
- 🔄 Modify seed data to test with different time ranges
- 🚀 Deploy to production environment
- 📝 Integrate with Airflow for automated data ingestion

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker logs time_series_db`, backend terminal output
3. Verify database state: `psql -d time_series -c "SELECT COUNT(*) FROM metrics.raw_data;"`

---

**Last Updated:** June 2026  
**Version:** 1.0.0
