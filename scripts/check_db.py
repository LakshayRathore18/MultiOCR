import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))
# Fallback: also try project root .env
load_dotenv(r"c:\CODING\MultiOCRnew\.env")

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

print('Connecting to PostgreSQL at', DB_HOST, 'port', DB_PORT, 'as', DB_USER)
try:
    conn = psycopg2.connect(dbname='postgres', user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database ORDER BY datname;")
    rows = cur.fetchall()
    print('Databases:')
    for r in rows:
        print(' -', r[0])
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
