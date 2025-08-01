import os, sys, socket

LISTEN_PORT = 9000

def init_nat():
    os.system("sysctl -w net.ipv4.ip_forward=1")
    os.system("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")
    print("Включён ip_forward и NAT")

def main():
    if os.geteuid() != 0:
        print("Запустите с root")
        sys.exit(1)
    init_nat()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))
    print(f"Слушаю UDP-пакеты от клиента на порту {LISTEN_PORT}")
    while True:
        raw, (client_ip, client_port) = sock.recvfrom(65535)
        try:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            raw_sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            raw_sock.sendto(raw, ("0.0.0.0", 0))
            raw_sock.close()
        except Exception as e:
            print("Ошибка отправки raw:", e)

if __name__ == "__main__":
    main()