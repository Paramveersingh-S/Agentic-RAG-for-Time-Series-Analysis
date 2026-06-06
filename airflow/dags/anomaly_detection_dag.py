from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

# Load environment variables (mock pathing for Airflow)
load_dotenv(os.path.join('/opt/airflow/dags/repo', '.env'))

# Assuming models module is accessible in Airflow's PYTHONPATH
import sys
sys.path.append('/opt/airflow/dags/repo')
from models.time_series_hub import TimeSeriesModelingHub

default_args = {
    'owner': 'ml_engineer',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def detect_anomalies_and_store_context(**context):
    """
    Retrieves recent data, runs Isolation Forest anomaly detection, 
    generates a Gemini summary for anomalies, and stores embeddings in pgvector.
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_time_series')
    engine = pg_hook.get_sqlalchemy_engine()
    
    query = """
        SELECT * FROM marts.mart_time_series_features
        WHERE metric_hour >= NOW() - INTERVAL '24 hours'
    """
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No data found for the last 24 hours.")
        return

    feature_cols = ['target_value', 'rolling_stddev_24h']
    all_anomalies = []
    
    for metric_name, group in df.groupby('metric_name'):
        result_df = TimeSeriesModelingHub.detect_anomalies_isolation_forest(
            group, feature_cols=feature_cols, contamination=0.05
        )
        anomalies = result_df[result_df['is_anomaly']]
        all_anomalies.append(anomalies)
        
    final_anomalies = pd.concat(all_anomalies)
    
    if final_anomalies.empty:
        print("No anomalies detected today.")
        return
        
    print(f"Detected {len(final_anomalies)} anomalies. Generating summaries and embeddings...")

    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    if os.environ.get("GOOGLE_API_KEY"):
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    else:
        print("Warning: GOOGLE_API_KEY not set. Using raw text and skipping vector embeddings.")
        llm = None
        embeddings_model = None

    for _, row in final_anomalies.iterrows():
        metric = row['metric_name']
        timestamp = row['metric_hour']
        value = row['target_value']
        rolling_avg = row['rolling_avg_24h']
        
        if pd.notna(rolling_avg) and rolling_avg > 0:
            pct_diff = ((value - rolling_avg) / rolling_avg) * 100
            diff_type = "drop" if pct_diff < 0 else "spike"
            magnitude = abs(pct_diff)
        else:
            diff_type = "deviation"
            magnitude = 0
            
        summary_text = f"A {magnitude:.1f}% {diff_type} in {metric} occurred on {timestamp}. Value was {value:.2f} compared to a rolling average of {rolling_avg:.2f}."
        
        try:
            if llm and embeddings_model:
                prompt = f"You are a financial data analyst. Briefly summarize this anomaly in one sentence: {summary_text}"
                response = llm.invoke(prompt)
                summary_text = response.content.strip()

                query_vector = embeddings_model.embed_query(summary_text)
                embedding_str = str(query_vector)
                
                insert_query = """
                    INSERT INTO embeddings.documents (timestamp, source_type, content, embedding)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (timestamp, 'anomaly_explanation', summary_text, embedding_str))
            else:
                # If no key, we skip storing because vector column requires 1536 float array
                pass
                
        except Exception as e:
            print(f"Error calling Gemini API or inserting to DB: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Anomaly processing complete.")

with DAG(
    'daily_anomaly_detection_and_embedding',
    default_args=default_args,
    description='Run Isolation Forest daily, generate Gemini summaries, and store embeddings',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['time-series', 'ml', 'anomaly', 'rag'],
) as dag:

    detect_task = PythonOperator(
        task_id='detect_and_embed_anomalies',
        python_callable=detect_anomalies_and_store_context,
        provide_context=True,
    )

    detect_task
