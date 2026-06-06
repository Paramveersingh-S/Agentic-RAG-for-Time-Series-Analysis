# Master Prompt: Agentic RAG for Time-Series Analysis

## Context and Objective
You are an Expert Data Engineer, Machine Learning Specialist, and AI Architect. I want to build an end-to-end system that combines time-series forecasting algorithms with a Multi-Agent Retrieval-Augmented Generation (RAG) pipeline. 

The goal is to create a natural language conversational interface where a user can ask complex questions about time-series data (e.g., "Why did our server traffic drop last Tuesday, and what is the forecast for next week?"). The system must autonomously query databases, run forecasting models, retrieve historical anomaly context, and synthesize an answer.

## Target Tech Stack
* **Orchestration:** Apache Airflow
* **Data Transformation:** dbt (Data Build Tool)
* **Database & Vector Store:** PostgreSQL with the `pgvector` extension
* **Agent Framework:** LangGraph (Python)
* **LLM Framework:** LangChain / OpenAI API (or local equivalent)
* **Time-Series Algorithms:** ARIMA/Prophet (Baseline), XGBoost (ML), LSTM (Deep Learning), Isolation Forests (Anomaly Detection)

---

## Architectural Requirements

Please generate the necessary code, configuration files, and architectural explanations to satisfy the following five phases.

### Phase 1: Data Ingestion and Storage (Postgres)
Design the database schema for a PostgreSQL instance that acts as both a traditional data warehouse and a Vector Database. 
* Create standard relational tables to store raw time-series metrics.
* Enable the `pgvector` extension.
* Create a schema for a vector table that will store embeddings of textual logs, metadata, and anomaly explanations.

### Phase 2: The ETL Pipeline (Airflow & dbt)
Write the Apache Airflow DAGs and dbt models required to clean and transform the raw data.
* **Airflow DAG:** Schedule a daily job to ingest mock time-series data into Postgres.
* **dbt Models:** Create staging and mart models to calculate rolling averages, lag variables, and seasonality metrics. Ensure the output is ready for machine learning consumption.

### Phase 3: Time-Series Modeling Hub
Implement a Python module containing a suite of time-series algorithms.
* Build a baseline forecasting function using ARIMA.
* Build a multivariate forecasting function using XGBoost, utilizing the dbt-generated lag features.
* Build an anomaly detection function using Isolation Forests.
* Include an Airflow task that runs the anomaly detector daily. If an anomaly is found, trigger a lightweight LLM prompt to generate a textual summary of the event (e.g., "A 15% drop in metric X occurred on Date Y") and store its embedding in the `pgvector` table.

### Phase 4: LangGraph Multi-Agent Workflow
Design a multi-agent system using LangGraph to handle user queries. I need the code for the following specific nodes:
* **Master Router Agent:** Analyzes the user's prompt and routes the task to the appropriate sub-agents.
* **SQL Database Agent:** Writes and executes safe SQL queries against the dbt mart tables to retrieve exact numerical historical data.
* **Time-Series Agent:** Dynamically calls the ARIMA or XGBoost functions from Phase 3 to generate a live forecast based on the user's requested time horizon.
* **Vector RAG Agent:** Takes the user's query, embeds it, and performs a similarity search in `pgvector` to find context on past anomalies or structural breaks in the data.

### Phase 5: Synthesis and Output
Create the final LangGraph node that acts as the Synthesis Agent. 
* This agent must take the exact numbers from the SQL Agent, the future predictions from the Time-Series Agent, and the historical context from the Vector RAG Agent.
* Instruct this agent to combine these inputs into a cohesive, conversational, and highly accurate natural language response.

---

## Execution Instructions
Please acknowledge this architecture. When I say "Begin Phase 1", provide the SQL scripts and Docker-compose file required to spin up PostgreSQL with `pgvector`. Do not generate the entire project at once; we will proceed phase by phase.