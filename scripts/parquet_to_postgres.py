import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

def insert_with_psycopg2(df, connection_string):
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    
    # CRITICAL: Create the pgvector extension FIRST, before registering
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    
    # NOW register the vector type with psycopg2
    register_vector(conn)
    
    # Get vector dimension from your data
    # Assuming you have a column with embeddings - adjust the column name as needed
    vector_column = 'embedding'  # Change this to your actual vector column name
    vector_dim = len(df.iloc[0][vector_column])
    
    # Create table with appropriate columns
    cur.execute("""
        DROP TABLE IF EXISTS demo;
        CREATE TABLE demo (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding vector(%s)
        )
    """, (vector_dim,))
    
    # Prepare data for batch insertion
    # Convert DataFrame rows to list of tuples
    data_list = [
        (row['content'], row[vector_column].tolist())  # Convert numpy array to list
        for _, row in df.iterrows()
    ]
    
    # Batch insert using execute_values (much faster than individual inserts)
    execute_values(
        cur,
        "INSERT INTO demo (content, embedding) VALUES %s",
        data_list,
        template="(%s, %s::vector)"  # Cast to vector type
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print("Data successfully inserted!")

# Read your parquet file
df = pd.read_parquet('data/wiki-en-subsampled.parquet')
df.columns = [c.lower() for c in df.columns]

# Insert the data
insert_with_psycopg2(df, 'postgresql://postgres:changeme@localhost:5432/demo')
