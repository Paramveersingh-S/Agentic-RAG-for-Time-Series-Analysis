-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Schema for traditional time-series metrics
CREATE SCHEMA IF NOT EXISTS metrics;

-- Relational table to store raw time-series metrics
CREATE TABLE IF NOT EXISTS metrics.raw_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    tags JSONB
);

-- Create an index on the timestamp and metric name for faster querying
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp_name ON metrics.raw_data(timestamp, metric_name);

-- Schema for vector embeddings
CREATE SCHEMA IF NOT EXISTS embeddings;

-- Vector table to store embeddings of textual logs, metadata, and anomaly explanations
-- Assuming an embedding dimension of 1536 (common for OpenAI's text-embedding-3-small or text-embedding-ada-002)
CREATE TABLE IF NOT EXISTS embeddings.documents (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source_type VARCHAR(50) NOT NULL, -- e.g., 'log', 'metadata', 'anomaly_explanation'
    content TEXT NOT NULL,            -- The original text content
    embedding VECTOR(1536)            -- The vector embedding
);

-- Create an HNSW index on the embedding column for efficient similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings.documents USING hnsw (embedding vector_l2_ops);
