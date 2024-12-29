import sqlite3
from bs4 import BeautifulSoup
from flask_cors import CORS
from flask import Flask, request, jsonify, stream_with_context, Response
from lxml import etree
from pathlib import Path

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

    html_content = parse_fb2_to_html(file_path)
    #html_path = f"./books/{fb2_file.filename}.html"

    soup = BeautifulSoup(html_content, "html.parser")

     # Разделяем HTML на страницы (например, по параграфам)
    page_size = 5000  # Ориентировочный размер страницы в символах
    pages = []
    current_page = ""
    current_size = 0

    for element in soup.find_all(True):  # Проходим по всем тегам
        element_str = str(element)
        if current_size + len(element_str) > page_size:
            # Завершаем текущую страницу
            pages.append(current_page)
            current_page = ""
            current_size = 0
        current_page += element_str
        current_size += len(element_str)

    # Добавляем последнюю страницу
    if current_page:
        pages.append(current_page)

    # Создаем папку для книги
    output_dir = Path(f"./books/{fb2_file.filename}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем страницы в файлы
    for i, page_content in enumerate(pages):
        page_file = output_dir / f"{i + 1}.html"
        with open(page_file, "w", encoding="utf-8") as page:
            page.write(page_content)

    # with open(html_path, 'w', encoding='utf-8') as file:
    #     file.write(html_content)

    name = request.form.get("name")

    with get_connect() as conn:
        cursor = conn.cursor()
        #cursor.execute("INSERT INTO books (title, file_path) VALUES (?, ?)", (name, file_path))
        cursor.execute("INSERT INTO books (title, file_path) VALUES (?, ?)", (name, html_path))
        
        conn.commit()
    return jsonify({"message": "Файл успешно загружен"}), 200

@app.route("/get-html/<int:book_id>", methods=["GET"])
def get_html(book_id):
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
    #html_content = parse_fb2_to_html(file_path)
    html_content = ""
    with open(file_path, encoding='utf-8') as file:
        html_content = file.read()
    if not html_content:
        print("Ошибка при обработке файла")
        return jsonify({"error": "Ошибка при обработке файла"}), 500

    #Возвращаем HTML контент частями
    def generate_html():
        chunk_size = 1024  # Размер чанка в байтах
        for i in range(0, len(html_content), chunk_size):
            yield html_content[i:i + chunk_size]

    return Response(stream_with_context(generate_html()), content_type="text/html")
    #return html_content

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
