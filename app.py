# from flask import Flask, jsonify
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


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Эндпоинт для загрузки FB2 файла и его конвертации
    """
    if "file" not in request.files:
        return jsonify({"error": "Файл не найден"}), 400

    fb2_file = request.files["file"]
    file_path = f"./uploads/{fb2_file.filename}"
    fb2_file.save(file_path)

    html_content = parse_fb2_to_html(file_path)
    if not html_content:
        return jsonify({"error": "Ошибка при обработке файла"}), 500

    # Возвращаем HTML контент частями
    def generate_html():
        chunk_size = 1024  # Размер чанка в байтах
        for i in range(0, len(html_content), chunk_size):
            yield html_content[i:i + chunk_size]

    return Response(stream_with_context(generate_html()), content_type="text/html")


if __name__ == "__main__":
    app.run(debug=True)
