import sqlite3

# Подключение к базе данных (или создание новой)
db = sqlite3.connect('books.db')
cursor = db.cursor()

# Создание таблицы
cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT,
        file_path TEXT NOT NULL,
        pages_amount INTEGER
    )
''')
db.commit()