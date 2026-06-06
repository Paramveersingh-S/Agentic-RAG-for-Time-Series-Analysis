from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI
import os

# Assuming models module is accessible in Airflow's PYTHONPATH
import sys
sys.path.append('/opt/airflow/dags/repo') # Mock path where code might reside
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
    generates an LLM summary for anomalies, and stores embeddings in pgvector.
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_time_series')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # 1. Fetch recent data from the dbt mart
    # We look at the last 24 hours of data
    query = """
        SELECT * FROM marts.mart_time_series_features
        WHERE metric_hour >= NOW() - INTERVAL '24 hours'
    """
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No data found for the last 24 hours.")
        return

    # 2. Run Anomaly Detection
    # Using target_value and rolling standard deviation as features
    feature_cols = ['target_value', 'rolling_stddev_24h']
    
    # We group by metric to detect anomalies per metric
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

    # 3. LLM Setup for generation and embedding
    # In a real setup, api_key should come from Airflow Connections/Variables
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "mock-key"))
    
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    for _, row in final_anomalies.iterrows():
        metric = row['metric_name']
        timestamp = row['metric_hour']
        value = row['target_value']
        rolling_avg = row['rolling_avg_24h']
        
        # Calculate percentage drop or spike
        if pd.notna(rolling_avg) and rolling_avg > 0:
            pct_diff = ((value - rolling_avg) / rolling_avg) * 100
            diff_type = "drop" if pct_diff < 0 else "spike"
            magnitude = abs(pct_diff)
        else:
            diff_type = "deviation"
            magnitude = 0
            
        # Generate lightweight LLM prompt summary
        # For cost/speed in this mock, we template it directly if LLM is unavailable,
        # but normally we'd call the LLM to write a natural language summary.
        summary_text = f"A {magnitude:.1f}% {diff_type} in {metric} occurred on {timestamp}. Value was {value:.2f} compared to a rolling average of {rolling_avg:.2f}."
        
        try:
            # Optionally enhance with LLM if a real key is present
            if os.environ.get("OPENAI_API_KEY"):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a data analyst. Briefly summarize this anomaly in one sentence."},
                        {"role": "user", "content": summary_text}
                    ],
                    max_tokens=50
                )
                summary_text = response.choices[0].message.content.strip()

            # Generate Embedding
            emb_response = client.embeddings.create(
                input=summary_text,
                model="text-embedding-3-small"
            )
            embedding = emb_response.data[0].embedding
            
            # Format embedding list to string for pgvector insertion (e.g. '[0.1, 0.2, ...]')
            embedding_str = str(embedding)
            
            # 4. Store in pgvector table
            insert_query = """
                INSERT INTO embeddings.documents (timestamp, source_type, content, embedding)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (timestamp, 'anomaly_explanation', summary_text, embedding_str))
            
        except Exception as e:
            print(f"Error calling OpenAI API or inserting to DB: {e}")
            # Fallback handling could go here

    conn.commit()
    cursor.close()
    conn.close()
    print("Anomaly processing complete.")

with DAG(
    'daily_anomaly_detection_and_embedding',
    default_args=default_args,
    description='Run Isolation Forest daily, generate LLM summaries, and store embeddings',
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
