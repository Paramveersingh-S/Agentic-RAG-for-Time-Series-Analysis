import yfinance as yf
from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime

def seed_database():
    """
    A standalone script to ingest real financial data into Postgres,
    bypassing Airflow so you can easily test the project locally.
    """
    print("Connecting to PostgreSQL...")
    engine = create_engine("postgresql://admin:password@localhost:5432/time_series")
    
    tickers = ['AAPL', 'GOOGL', '^GSPC']
    insert_queries = []
    
    for ticker in tickers:
        print(f"Fetching 30 days of data for {ticker}...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo", interval="1d")
        
        for date, row in hist.iterrows():
            timestamp = date.to_pydatetime()
            close_price = float(row['Close'])
            volume = float(row['Volume'])
            
            # Price
            insert_queries.append(f"""
                INSERT INTO metrics.raw_data (timestamp, metric_name, metric_value, tags)
                VALUES ('{timestamp.isoformat()}', '{ticker}', {close_price}, '{{"type": "price"}}');
            """)
            
            # Volume
            insert_queries.append(f"""
                INSERT INTO metrics.raw_data (timestamp, metric_name, metric_value, tags)
                VALUES ('{timestamp.isoformat()}', '{ticker}_VOL', {volume}, '{{"type": "volume"}}');
            """)
            
    print(f"Inserting {len(insert_queries)} records into the database...")
    with engine.begin() as conn:
        for query in insert_queries:
            conn.execute(query)
            
    print("✅ Database successfully seeded with real data!")

if __name__ == "__main__":
    seed_database()
