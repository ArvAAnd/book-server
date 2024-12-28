#import file app.py
from app import get_connect

with get_connect() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    rows = cursor.fetchall()
    for row in rows:
        print(dict(row))