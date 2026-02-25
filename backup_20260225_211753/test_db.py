import os
from dotenv import load_dotenv
import psycopg
import sys

load_dotenv()
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('? DATABASE_URL not found in .env')
    sys.exit(1)

print(f'Connecting to: {db_url}')
try:
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print('? Connection successful, SELECT 1 returned:', cur.fetchone())
    cur.close()
    conn.close()
except Exception as e:
    print(f'? Connection failed: {e}')
