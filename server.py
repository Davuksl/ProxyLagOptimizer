from flask import Flask, request, jsonify
from flask_cors import CORS
import python_socks
import threading
import socket
import time
import os

app = Flask(__name__)
# Explicitly allow CORS for localhost and file:// origins
CORS(app, resources={r"/*": {"origins": ["http://localhost:8000", "file://*", "https://*"]}}, supports_credentials=True)

# Конфигурация прокси
PROXY_HOST = "0.0.0.0"
PROXY_PORT = int(os.environ.get('SOCKS_PORT', 1080))  # SOCKS5 port
proxy_thread = None
proxy_running = False

def run_proxy_server():
    global proxy_running
    try:
        print(f"Starting SOCKS5 server on {PROXY_HOST}:{PROXY_PORT}")
        server = python_socks.sync.socks5.Socks5Server(host=PROXY_HOST, port=PROXY_PORT)
        proxy_running = True
        server.serve_forever()
    except Exception as e:
        proxy_running = False
        print(f"Ошибка прокси: {type(e).__name__}: {str(e)}")

@app.route('/connect', methods=['POST', 'OPTIONS'])
def connect():
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = jsonify({"status": "OK"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    try:
        print("Received /connect request")
        if proxy_thread is None or not proxy_thread.is_alive():
            proxy_thread = threading.Thread(target=run_proxy_server)
            proxy_thread.daemon = True
            proxy_thread.start()
            time.sleep(1)
        ping = measure_ping("8.8.8.8")
        response = jsonify({
            "status": "Подключено к ProxyLag",
            "ping": f"{ping} ms",
            "host": "proxylagoptimizer.onrender.com",
            "port": PROXY_PORT
        })
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        return response
    except Exception as e:
        print(f"Ошибка в /connect: {type(e).__name__}: {str(e)}")
        return jsonify({"status": f"Ошибка: {str(e)}", "ping": "N/A"}), 500

@app.route('/disconnect', methods=['POST', 'OPTIONS'])
def disconnect():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "OK"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    try:
        print("Received /disconnect request")
        global proxy_thread, proxy_running
        if proxy_thread and proxy_running:
            proxy_running = False
            proxy_thread = None  # Note: Proper socket shutdown needed
        response = jsonify({"status": "Отключено", "ping": "N/A"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        return response
    except Exception as e:
        print(f"Ошибка в /disconnect: {type(e).__name__}: {str(e)}")
        return jsonify({"status": f"Ошибка: {str(e)}", "ping": "N/A"}), 500

def measure_ping(host):
    try:
        start = time.time()
        socket.create_connection((host, 80), timeout=2).close()
        return round((time.time() - start) * 1000, 2)
    except Exception as e:
        print(f"Ошибка пинга: {type(e).__name__}: {str(e)}")
        return "N/A"

if __name__ == '__main__':
    flask_port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask on port {flask_port}")
    app.run(host='0.0.0.0', port=flask_port)