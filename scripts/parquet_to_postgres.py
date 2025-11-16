import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
# import ast

def insert_with_psycopg2(df, connection_string):
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    
    # Create the pgvector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    
    # Register the vector type with psycopg2
    register_vector(conn)
    
    # Your actual column is 'embeddings', not 'embedding'
    vector_column = 'embeddings'
    
    # Parse the string representation of arrays into actual numpy arrays
    # The embeddings column contains string representations of numpy arrays
    def parse_embedding(embedding_str):
        if isinstance(embedding_str, str):
            # Remove extra whitespace and convert scientific notation
            cleaned = ' '.join(embedding_str.split())
            # Convert to list of floats
            return [float(x) for x in cleaned.split()]
        elif isinstance(embedding_str, np.ndarray):
            return embedding_str.tolist()
        else:
            return embedding_str
    
    # Convert string embeddings to lists
    df['embeddings_list'] = df[vector_column].apply(parse_embedding)
    
    # Get vector dimension from the first row
    vector_dim = len(df.iloc[0]['embeddings_list'])
    print(f"Vector dimension detected: {vector_dim}")
    
    # Create table with all the columns from your data
    cur.execute("""
        DROP TABLE IF EXISTS demo CASCADE;
        CREATE TABLE demo (
            id BIGINT PRIMARY KEY,
            url TEXT,
            title TEXT,
            text TEXT,
            embeddings vector(%s)
        )
    """, (vector_dim,))
    
    # Prepare data for batch insertion
    data_list = [
        (
            int(row['id']),
            row['url'],
            row['title'],
            row['text'],
            row['embeddings_list']  # Already converted to list
        )
        for _, row in df.iterrows()
    ]
    
    # Batch insert using execute_values
    execute_values(
        cur,
        "INSERT INTO demo (id, url, title, text, embeddings) VALUES %s",
        data_list,
        template="(%s, %s, %s, %s, %s::vector)"
    )
    
    conn.commit()
    
    # Create indexes for fast similarity search
    print("Creating indexes...")
    cur.execute("""
        CREATE INDEX ON demo USING hnsw (embeddings vector_cosine_ops);
        CREATE INDEX ON demo (id);
    """)
    conn.commit()
    
    # Verify insertion
    cur.execute("SELECT COUNT(*) FROM demo")
    count = cur.fetchone()[0]
    print(f"Successfully inserted {count} rows")
    
    cur.close()
    conn.close()
    print("Data successfully inserted!")


def insert_with_psycopg2_numpy(df, connection_string):
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    
    # Create extension and register
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    
    # Get vector dimension
    vector_dim = len(df.iloc[0]['embeddings'])
    
    # Create table
    cur.execute("""
        DROP TABLE IF EXISTS demo CASCADE;
        CREATE TABLE demo (
            id BIGINT PRIMARY KEY,
            url TEXT,
            title TEXT,
            text TEXT,
            embeddings vector(%s)
        )
    """, (vector_dim,))
    
    # Convert numpy arrays to lists
    df['embeddings'] = df['embeddings'].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)
    
    # Insert data
    data_list = df[['id', 'url', 'title', 'text', 'embeddings']].values.tolist()
    
    execute_values(
        cur,
        "INSERT INTO demo (id, url, title, text, embeddings) VALUES %s",
        data_list,
        template="(%s, %s, %s, %s, %s::vector)"
    )
    
    conn.commit()
    cur.close()
    conn.close()



# Read your parquet file
print("Reading parquet file...")
df = pd.read_parquet('data/wiki-en-subsampled.parquet')
df.columns = [c.lower() for c in df.columns]

print(f"DataFrame shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# # Insert the data
# insert_with_psycopg2(df, 'postgresql://postgres:changeme@localhost:5432/demo')

insert_with_psycopg2_numpy(df, 'postgresql://postgres:changeme@localhost:5432/demo')
