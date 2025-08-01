from flask import Flask, request, jsonify
from flask_cors import CORS
import python_socks
import threading
import socket
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["file://*"]}})  # Allow file:// origins

# Конфигурация прокси
PROXY_HOST = "0.0.0.0"
PROXY_PORT = int(os.environ.get('PORT', 1080))
proxy_thread = None
proxy_running = False

def run_proxy_server():
    global proxy_running
    try:
        server = python_socks.sync.socks5.Socks5Server(host=PROXY_HOST, port=PROXY_PORT)
        proxy_running = True
        server.serve_forever()
    except Exception as e:
        proxy_running = False
        print(f"Ошибка прокси: {e}")

@app.route('/connect', methods=['POST'])
def connect():
    global proxy_thread, proxy_running
    try:
        if proxy_thread is None or not proxy_thread.is_alive():
            proxy_thread = threading.Thread(target=run_proxy_server)
            proxy_thread.daemon = True
            proxy_thread.start()
            time.sleep(1)
        ping = measure_ping("8.8.8.8")
        return jsonify({
            "status": "Подключено к ProxyLag",
            "ping": f"{ping} ms",
            "host": "proxylagoptimizer.onrender.com",
            "port": PROXY_PORT
        })
    except Exception as e:
        return jsonify({"status": f"Ошибка: {str(e)}", "ping": "N/A"})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    global proxy_thread, proxy_running
    try:
        if proxy_thread and proxy_running:
            proxy_running = False
            proxy_thread = None  # Note: Proper socket shutdown needed
        return jsonify({"status": "Отключено", "ping": "N/A"})
    except Exception as e:
        return jsonify({"status": f"Ошибка: {str(e)}", "ping": "N/A"})

def measure_ping(host):
    try:
        start = time.time()
        socket.create_connection((host, 80), timeout=2).close()
        return round((time.time() - start) * 1000, 2)
    except:
        return "N/A"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))