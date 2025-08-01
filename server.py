from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import socket
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:8000", "file://*", "https://*"]}}, supports_credentials=True)

PROXY_HOST = "0.0.0.0"
PROXY_PORT = int(os.environ.get('SOCKS_PORT', 1081))
proxy_thread = None
proxy_running = False
proxy_socket = None

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        src.close()
        dst.close()

def handle_client(client, addr):
    try:
        client.recv(262)
        client.sendall(b"\x05\x00")

        req = client.recv(1024)
        if len(req) < 7 or req[1] != 1:
            client.close()
            return

        address_type = req[3]
        if address_type == 1:
            ip = socket.inet_ntoa(req[4:8])
            port = int.from_bytes(req[8:10], 'big')
        elif address_type == 3:
            domain_len = req[4]
            domain = req[5:5+domain_len].decode()
            ip = socket.gethostbyname(domain)
            port = int.from_bytes(req[5+domain_len:7+domain_len], 'big')
        else:
            client.close()
            return

        remote = socket.create_connection((ip, port))
        client.sendall(b"\x05\x00\x00\x01" + socket.inet_aton(ip) + port.to_bytes(2, 'big'))

        threading.Thread(target=forward, args=(client, remote), daemon=True).start()
        threading.Thread(target=forward, args=(remote, client), daemon=True).start()

    except Exception as e:
        print(f"[ERROR] Client {addr} error: {e}")
        client.close()

def run_proxy_server():
    global proxy_running, proxy_socket
    try:
        print(f"Starting SOCKS5 server on {PROXY_HOST}:{PROXY_PORT}")
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind((PROXY_HOST, PROXY_PORT))
        proxy_socket.listen(100)
        proxy_running = True
        while proxy_running:
            client, addr = proxy_socket.accept()
            print(f"New client: {addr}")
            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()
    except Exception as e:
        print(f"[SOCKS5 ERROR] {e}")
        proxy_running = False
        if proxy_socket:
            proxy_socket.close()

@app.route('/connect', methods=['POST', 'OPTIONS'])
def connect():
    global proxy_thread, proxy_running
    if request.method == 'OPTIONS':
        response = jsonify({"status": "OK"})
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response

    try:
        print("[CONNECT] Request received")
        if proxy_thread is None or not proxy_thread.is_alive():
            print("Starting proxy thread...")
            proxy_thread = threading.Thread(target=run_proxy_server)
            proxy_thread.daemon = True
            proxy_thread.start()
            time.sleep(3)
            if not proxy_running:
                raise RuntimeError("Proxy server failed to start")

        ping = measure_ping("8.8.8.8")
        response = jsonify({
            "status": "Подключено к ProxyLag",
            "ping": f"{ping} ms",
            "host": "proxylagoptimizer.onrender.com",
            "port": PROXY_PORT
        })
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        return response
    except Exception as e:
        print(f"[CONNECT ERROR] {e}")
        return jsonify({"status": f"Ошибка: {e}", "ping": "N/A"}), 500

@app.route('/disconnect', methods=['POST', 'OPTIONS'])
def disconnect():
    global proxy_running, proxy_socket, proxy_thread
    if request.method == 'OPTIONS':
        response = jsonify({"status": "OK"})
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response

    try:
        print("[DISCONNECT] Request received")
        if proxy_socket:
            proxy_running = False
            proxy_socket.close()
            proxy_socket = None
            proxy_thread = None

        response = jsonify({"status": "Отключено", "ping": "N/A"})
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
        return response
    except Exception as e:
        print(f"[DISCONNECT ERROR] {e}")
        return jsonify({"status": f"Ошибка: {e}", "ping": "N/A"}), 500

def measure_ping(host):
    try:
        start = time.time()
        socket.create_connection((host, 80), timeout=2).close()
        return round((time.time() - start) * 1000, 2)
    except:
        return "N/A"

if __name__ == '__main__':
    flask_port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=flask_port)