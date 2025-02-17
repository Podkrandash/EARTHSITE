import http.server
import socketserver
import os

# Конфигурация
PORT = 8000
HOST = 'localhost'

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Добавляем CORS заголовки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        # Обработка корневого пути
        if self.path == '/':
            self.path = '/index.html'
        try:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            print(f"Ошибка при обработке запроса: {str(e)}")
            self.send_error(500, "Internal Server Error")

def run_server():
    try:
        # Разрешаем повторное использование порта
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer((HOST, PORT), RequestHandler) as httpd:
            print(f"Сервер запущен на http://{HOST}:{PORT}")
            print("Для остановки сервера нажмите Ctrl+C")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == '__main__':
    run_server() 