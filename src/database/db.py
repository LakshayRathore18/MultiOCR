import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db():
    """
    Establishes and returns a PostgreSQL database connection.
    Credentials are loaded from environment variables for security.
    """
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "multiocrDB"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )
