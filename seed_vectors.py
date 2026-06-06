"""
Vector Store Seeding Script
Populates the embeddings.documents table with market context and historical insights.
This provides RAG context for the anomaly detection agent.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json
import psycopg2

# Load environment variables
load_dotenv()

def seed_vector_store():
    """
    Seeds the vector store with market insights and anomaly explanations.
    Uses dummy embeddings (zeros) since Google API only supports Gemini models.
    In production, replace with actual embedding service.
    """
    print("Connecting to PostgreSQL...")
    db_url = os.environ.get("DATABASE_URL", "postgresql://admin:password@localhost:5432/time_series")
    
    # Market context documents
    documents = [
        {
            "source_type": "market_insight",
            "content": "S&P 500 Index (^GSPC) represents the 500 largest US companies. Typically volatile during Fed announcements, earnings seasons, and geopolitical events. Recent performance affected by inflation concerns and interest rate changes."
        },
        {
            "source_type": "market_insight", 
            "content": "Apple Inc. (AAPL) is a mega-cap technology company. Stock price correlates with iPhone sales, services revenue, and App Store performance. Historically strong during holiday shopping season (Q4). Sensitive to semiconductor supply chain disruptions."
        },
        {
            "source_type": "market_insight",
            "content": "Alphabet Inc. (GOOGL) is primarily a search and advertising company. Revenue driven by Google Search ads, YouTube ads, and Cloud services. Stock price affected by regulatory scrutiny, ad market conditions, and AI developments."
        },
        {
            "source_type": "anomaly_explanation",
            "content": "Sharp price drop detected on specific date: This could be due to earnings miss, product recall, CEO departure, or market-wide correction. Always cross-reference with news events and market indicators."
        },
        {
            "source_type": "anomaly_explanation",
            "content": "Unusual trading volume spike: Can indicate major institutional buying/selling, merger speculation, or response to breaking news. High volume often confirms trend reversals."
        },
        {
            "source_type": "technical_analysis",
            "content": "During market corrections (>5% decline), tech stocks often lead the downside. Recovery typically follows after positive Fed signals or strong earnings. Support levels are key entry points for long-term investors."
        },
        {
            "source_type": "technical_analysis",
            "content": "Year-to-date performance: Tech-heavy indices like NASDAQ often outperform S&P 500 during growth periods but underperform during value rallies. Diversification between growth and value stocks is important."
        },
        {
            "source_type": "risk_context",
            "content": "Systematic risks affecting all stocks: Interest rate hikes, inflation, geopolitical tensions, recession fears. Idiosyncratic risks: Company-specific news, product launches, management changes."
        }
    ]
    
    # Create dummy embeddings (1536-dimensional zero vectors as placeholders)
    # In production, use: GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    dummy_embedding = [0.0] * 1536
    
    print(f"Seeding {len(documents)} documents into vector store...")
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        for doc in documents:
            # Insert with proper vector formatting for pgvector
            cursor.execute("""
                INSERT INTO embeddings.documents (source_type, content, embedding)
                VALUES (%s, %s, %s::vector)
            """, (
                doc["source_type"],
                doc["content"],
                json.dumps(dummy_embedding)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Vector store successfully seeded with market insights!")
        
        # Verify data was inserted
        engine = create_engine(db_url)
        with engine.connect() as con:
            result = con.execute(text("SELECT COUNT(*) FROM embeddings.documents"))
            count = result.scalar()
            print(f"   Total documents in vector store: {count}")
            
    except Exception as e:
        print(f"❌ Error seeding vector store: {e}")
        raise

if __name__ == "__main__":
    seed_vector_store()
