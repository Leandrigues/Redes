import socket

class Client:
    """Classe que representa um Cliente"""
    
    def __init__(self):
        self.socket = None

    def connect(self, port, ip):
        """Connect to server or to other client"""
        try:
            self.socket = socket.create_connection((ip,port))
        except:
            print(f"Could not connect to address {ip}:{port}")

        msg = bytes("Ola",'utf-8')
        print(msg)
        self.socket.sendmsg([msg])

        self.disconnect()

    def disconnect(self):
        print("Closing socket")
        self.socket.close()
