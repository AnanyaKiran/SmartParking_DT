from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())
conn.close()
