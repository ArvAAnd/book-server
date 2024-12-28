# from flask import Flask, jsonify
import sqlite3
from flask_cors import CORS
# import logging

# app = Flask(__name__)
# CORS(app)
# logging.basicConfig(level = logging.DEBUG)

# @app.route('/get-html', methods=['GET'])
# def serve_html():
#     try:
#         # Read the HTML content from the file
#         with open('books/The_Plagiarist__Wen_Chao_Gong__CHernoknichnik_v_Mire_Magov__LP__Readli.Net_645528_original_39a8a.html', 'r', encoding='utf-8') as file:
#             html_content = file.read()
#         return jsonify({"data": html_content})
#     except FileNotFoundError:
#         return jsonify({"data": "HTML file not found"})

# @app.route('/')
# def home():
#     return "Welcome to the home page!"

# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, request, jsonify, stream_with_context, Response
from lxml import etree

app = Flask(__name__)
CORS(app)

def get_connect():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

def parse_fb2_to_html(file_path):
    """
    Парсит FB2 файл и конвертирует его в HTML
    """
    try:
        tree = etree.parse(file_path)
        root = tree.getroot()
        namespace = {"fb2": "http://www.gribuser.ru/xml/fictionbook/2.0"}

        # Получаем заголовок книги
        title_info = root.find(".//fb2:title-info", namespaces=namespace)
        title = title_info.find(".//fb2:book-title", namespaces=namespace).text if title_info is not None else "Без названия"

        # Получаем главы книги
        body = root.find(".//fb2:body", namespaces=namespace)
        chapters = body.findall(".//fb2:section", namespaces=namespace)

        # Конвертируем каждую главу в HTML
        html_content = f"<h1>{title}</h1>"
        for chapter in chapters:
            chapter_title = chapter.find(".//fb2:title/fb2:p", namespaces=namespace)
            chapter_title_text = chapter_title.text if chapter_title is not None else "Без названия главы"
            html_content += f"<h2>{chapter_title_text}</h2>"

            # Добавляем текст главы
            paragraphs = chapter.findall(".//fb2:p", namespaces=namespace)
            for paragraph in paragraphs:
                html_content += f"<p>{paragraph.text}</p>"

        return html_content

    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")
        return None


@app.route("/add-book", methods=["POST"])
def upload_file():
    """
    Эндпоинт для загрузки FB2 файла и его конвертации
    """
    print(request)
    if "file" not in request.files:
        print("Файл не найден")
        return jsonify({"error": "Файл не найден"}), 400
    if "name" not in request.form:
        print("Имя не найдено")
        return jsonify({"error": "Имя не найдено"}), 400
    
    fb2_file = request.files.get("file")
    file_path = f"./uploads/{fb2_file.filename}"
    fb2_file.save(file_path)
    
    name = request.form.get("name")

    with get_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO books (title, file_path) VALUES (?, ?)", (name, file_path))
        conn.commit()
    return jsonify({"message": "Файл успешно загружен"}), 200

@app.route("/get-html/<int:book_id>", methods=["GET"])
def get_html(book_id):
    print(request)
    print(book_id)
    file_path = ""
    #with open('./listOfBooks.txt', 'r', encoding='utf-8') as file:
    with get_connect() as conn:
        #books = file.readlines()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        for book in books:
            # Разделяем строку по последнему ":" и получаем ID
            # parts = book.strip().rsplit(':')
            # print(parts)
            #if len(parts) == 2 and parts[0] == str(book_id):
                # Используем путь из первой части строки
                #print("Путь к файлу: " + parts[1].strip())
                #file_path = parts[1].strip()
                #break
            if book['id'] == book_id:
                file_path = book['file_path']
                break
        if file_path == "":
            # Если книга не найдена
            print("Книга не найдена")
            return jsonify({"error": "Книга не найдена"}), 404
    html_content = parse_fb2_to_html(file_path)
    if not html_content:
        print("Ошибка при обработке файла")
        return jsonify({"error": "Ошибка при обработке файла"}), 500

    # Возвращаем HTML контент частями
    def generate_html():
        chunk_size = 1024  # Размер чанка в байтах
        for i in range(0, len(html_content), chunk_size):
            yield html_content[i:i + chunk_size]

    return Response(stream_with_context(generate_html()), content_type="text/html")

@app.route("/get-all-books", methods=["GET"])
def get_books():
    with get_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        books = [{
            'id': book['id'],
            'title': book['title']
            }
            for book in books
        ]
        return jsonify(books)

@app.route("/get-genres-books", methods=["GET"])
def get_genres_books():
    with get_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        return jsonify([dict(book) for book in books])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
