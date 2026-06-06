# 📈 Agentic RAG for Time-Series Analysis

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![pgvector](https://img.shields.io/badge/pgvector-Enabled-success)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-Orchestration-orange?logo=apacheairflow)
![dbt](https://img.shields.io/badge/dbt-Transformations-FF694B?logo=dbt)
![LangGraph](https://img.shields.io/badge/LangGraph-Agents-blueviolet)

An end-to-end multi-agent Retrieval-Augmented Generation (RAG) system built to provide a conversational interface for complex time-series data. This architecture seamlessly merges traditional data engineering (Airflow, dbt, Postgres), machine learning (ARIMA, XGBoost, Isolation Forests), and modern AI orchestration (LangGraph, OpenAI) to dynamically answer complex questions about past metrics, future forecasts, and contextual anomaly explanations.

---

## 🏗️ Architecture Overview

The system is designed in a highly modular, full-stack architecture:

```mermaid
graph TD
    classDef db fill:#3366ff,stroke:#fff,stroke-width:2px,color:#fff;
    classDef agent fill:#ff9900,stroke:#fff,stroke-width:2px,color:#fff;
    classDef pipeline fill:#00cc66,stroke:#fff,stroke-width:2px,color:#fff;
    classDef ui fill:#e11d48,stroke:#fff,stroke-width:2px,color:#fff;

    subgraph Data & ETL Pipeline
        A[Airflow Ingestion with yfinance]:::pipeline -->|Real Market Data| B[(PostgreSQL Relational)]:::db
        B --> C[dbt Staging & Marts]:::pipeline
        C --> D[(PostgreSQL Marts)]:::db
    end
    
    subgraph Machine Learning Hub
        D --> E[Isolation Forest Anomaly Det.]:::pipeline
        E -->|Triggers| F[Gemini Context Generator]:::pipeline
        F -->|Embeddings| G[(pgvector Index)]:::db
    end
    
    subgraph LangGraph Multi-Agent System
        U[FastAPI Backend]:::ui --> H{Master Router}:::agent
        H -->|Numerical Queries| I[SQL Agent]:::agent
        I -->|Queries| D
        H -->|Predictions| J[Time-Series Agent]:::agent
        J -->|Fetches Data| D
        H -->|Anomaly Context| K[Vector RAG Agent]:::agent
        K -->|Similarity Search| G
        
        I --> L[Synthesis Agent]:::agent
        J --> L
        K --> L
        L --> M[Natural Language Response]
    end
    
    subgraph Web UI
        W[React / Vite Frontend]:::ui <--> U
    end
```

---

## ⚙️ Technical Details

### Phase 1: Data Storage (`pgvector`)
We use a unified **PostgreSQL 16** instance as both a traditional analytical warehouse and a Vector Database.

### Phase 2: ETL Pipeline (Airflow & dbt)
*   **Apache Airflow:** Orchestrates daily ingestion of real stock market data (Apple, Google, S&P 500) via `yfinance`.
*   **dbt (Data Build Tool):** Transforms raw data into staging and mart models, generating critical ML features (rolling averages, 1h/24h lag variables, standard deviations).

### Phase 3: Time-Series Modeling Hub
A dedicated Python module (`time_series_hub.py`) housing standard algorithms:
*   **ARIMA:** For baseline univariate forecasting.
*   **XGBoost:** For multivariate forecasting utilizing dbt-generated lag features.
*   **Isolation Forests:** For unsupervised anomaly detection. Anomalies trigger **Gemini** to write a short contextual summary, which is embedded via `GoogleGenerativeAIEmbeddings` and saved to `pgvector`.

### Phase 4 & 5: LangGraph Agents & Full-Stack UI
A stateful, multi-agent workflow orchestrated via LangGraph, exposed through a Web UI:
1.  **FastAPI Backend:** Provides the API layer for the agentic workflow.
2.  **React (Vite) Frontend:** A premium, dark-mode web application featuring real-time chat and dynamic `Recharts` graphs overlaying historical data with AI forecasts.
3.  **Agents:** Master Router, SQL Agent, Time-Series Agent, Vector RAG Agent, and Synthesis Agent work together utilizing **Gemini 1.5 Flash** to analyze data and synthesize conversational responses.

---

## 🚀 Getting Started

### Prerequisites
*   Docker & Docker Compose
*   Python 3.10+
*   OpenAI API Key

### Installation

1.  **Start the Database:**
    ```bash
    # Spins up PostgreSQL with pgvector and initializes the schemas
    docker compose up -d
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt 
    # (Ensure you install apache-airflow, dbt-postgres, xgboost, scikit-learn, langgraph, langchain-openai, sqlalchemy, pandas, statsmodels)
    ```

3.  **Setup Environment Variables:**
    ```bash
    export OPENAI_API_KEY="your-api-key-here"
    ```

4.  **Run the LangGraph Application:**
    ```bash
    python agents/main_graph.py
    ```

---
*Generated as part of the Agentic RAG for Time-Series Analysis architecture build.*
