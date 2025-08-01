from flask import Flask, request, jsonify
from flask_cors import CORS
import python_socks
import threading
import socket
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:8000", "file://*", "https://*"]}}, supports_credentials=True)

# Конфигурация прокси
PROXY_HOST = "0.0.0.0"
PROXY_PORT = int(os.environ.get('SOCKS_PORT', 1081))
proxy_thread = None
proxy_running = False
proxy_server = None

def run_proxy_server():
    global proxy_running, proxy_server
    try:
        print(f"Attempting to start SOCKS5 server on {PROXY_HOST}:{PROXY_PORT}")
        # Check if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((PROXY_HOST, PROXY_PORT))
            sock.close()
        except OSError as e:
            print(f"Port {PROXY_PORT} binding failed: {str(e)}")
            raise
        # Use the correct Socks5Server class
        from python_socks.sync import Socks5Server
        proxy_server = Socks5Server(host=PROXY_HOST, port=PROXY_PORT)
        proxy_running = True
        print(f"SOCKS5 server running on {PROXY_HOST}:{PROXY_PORT}")
        proxy_server.serve_forever()
    except Exception as e:
        proxy_running = False
        print(f"Ошибка запуска SOCKS5: {type(e).__name__}: {str(e)}")
        raise

@app.route('/connect', methods=['POST', 'OPTIONS'])
def connect():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "OK"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    try:
        print("Received /connect request")
        global proxy_thread, proxy_running
        if proxy_thread is None or not proxy_thread.is_alive():
            print("Starting new SOCKS5 proxy thread")
            proxy_thread = threading.Thread(target=run_proxy_server)
            proxy_thread.daemon = True
            proxy_thread.start()
            time.sleep(3)
            if not proxy_running:
                raise RuntimeError("SOCKS5 server failed to start")
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
        global proxy_thread, proxy_running, proxy_server
        if proxy_thread and proxy_running and proxy_server:
            print("Stopping SOCKS5 proxy")
            proxy_running = False
            proxy_server.shutdown()
            proxy_server = None
            proxy_thread = None
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