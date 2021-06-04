import socket
from random import randint

class Server:
    HOST = '127.0.0.1'

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, port):
        try:
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)
        except OSError:
            # Por enquanto, só pra evitar o bug da porta ficar ocupada
            # depois de finalizar o processo, tô adicionando um random
            # pra pegar uma porta desocupada
            port += randint(1, 99)
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)

        self.socket.listen()

        conn, addr = self.socket.accept()
        while True:
            print("Received connection from", addr)
            # ct = client_thread(conn) # Pra no futuro usar threads
            # ct.run()
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)
            print(f"Received: {data}")
        self.disconnect()

    def disconnect(self):
        print("Closing socket")
        self.socket.close()
