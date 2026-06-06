from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import random

# Default arguments for the DAG
default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def generate_and_ingest_mock_data(**context):
    """
    Generates mock time-series data for the current execution date and inserts it into Postgres.
    """
    execution_date = context['execution_date']
    
    # Example metric names
    metrics = ['server_requests', 'cpu_utilization', 'active_users']
    
    # Establish connection using PostgresHook
    # Note: Requires an Airflow connection named 'postgres_time_series'
    pg_hook = PostgresHook(postgres_conn_id='postgres_time_series')
    
    # Generate 24 hourly data points for the execution date
    insert_queries = []
    for hour in range(24):
        timestamp = execution_date.replace(hour=hour, minute=0, second=0, microsecond=0)
        
        for metric_name in metrics:
            # Generate a semi-random value, perhaps with some artificial daily seasonality
            base_value = 100 if metric_name == 'server_requests' else 50
            seasonality = 20 * (1 if 8 <= hour <= 18 else -1) # Higher during work hours
            noise = random.uniform(-10, 10)
            
            metric_value = base_value + seasonality + noise
            
            # Prevent negative values for these specific metrics
            metric_value = max(0, metric_value)
            
            # Construct the SQL query
            query = f"""
                INSERT INTO metrics.raw_data (timestamp, metric_name, metric_value, tags)
                VALUES ('{timestamp.isoformat()}', '{metric_name}', {metric_value}, '{{"environment": "production"}}')
            """
            insert_queries.append(query)
            
    # Execute all insertions
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    for query in insert_queries:
        cursor.execute(query)
    
    connection.commit()
    cursor.close()
    connection.close()

# Define the DAG
with DAG(
    'ingest_mock_time_series_data',
    default_args=default_args,
    description='A DAG to ingest mock time-series data daily into PostgreSQL',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['time-series', 'ingestion'],
) as dag:

    ingest_task = PythonOperator(
        task_id='generate_and_ingest_mock_data',
        python_callable=generate_and_ingest_mock_data,
        provide_context=True,
    )

    ingest_task
