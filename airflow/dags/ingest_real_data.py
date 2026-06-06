from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def ingest_yfinance_data(**context):
    """
    Fetches real historical stock data using yfinance and inserts it into Postgres.
    We fetch the last 30 days of data for a few tickers to provide a rich dataset.
    """
    tickers = ['AAPL', 'GOOGL', '^GSPC'] # Apple, Google, S&P 500
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_time_series')
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    
    insert_queries = []
    
    for ticker in tickers:
        print(f"Fetching data for {ticker}...")
        stock = yf.Ticker(ticker)
        # Get historical market data (last 30 days, 1h intervals if possible, or 1d)
        # Using 1d intervals but casting to midnight for our 'hourly' or 'daily' marts
        hist = stock.history(period="1mo", interval="1d")
        
        for date, row in hist.iterrows():
            timestamp = date.to_pydatetime()
            close_price = float(row['Close'])
            volume = float(row['Volume'])
            
            # Insert Price
            query_price = f"""
                INSERT INTO metrics.raw_data (timestamp, metric_name, metric_value, tags)
                VALUES ('{timestamp.isoformat()}', '{ticker}', {close_price}, '{{"type": "price"}}')
            """
            insert_queries.append(query_price)
            
            # Insert Volume
            query_vol = f"""
                INSERT INTO metrics.raw_data (timestamp, metric_name, metric_value, tags)
                VALUES ('{timestamp.isoformat()}', '{ticker}_VOL', {volume}, '{{"type": "volume"}}')
            """
            insert_queries.append(query_vol)
            
    # Execute insertions
    for query in insert_queries:
        try:
            cursor.execute(query)
        except Exception as e:
            print(f"Error executing query: {e}")
            connection.rollback()
            
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Successfully inserted {len(insert_queries)} real data points into Postgres.")

with DAG(
    'ingest_real_financial_data',
    default_args=default_args,
    description='A DAG to ingest real yfinance data into PostgreSQL',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['time-series', 'ingestion', 'finance'],
) as dag:

    ingest_task = PythonOperator(
        task_id='ingest_yfinance_data',
        python_callable=ingest_yfinance_data,
        provide_context=True,
    )

    ingest_task
