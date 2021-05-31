import socket

class Client:
    """Classe que representa um Cliente"""
    
    def __init__(self):
        self.socket = None

    def start(self,port,ip):
        """Connects to server and reads user input."""

        self.connect(port,ip)
        self.command_loop()
        self.disconnect()

    def connect(self, port, ip):
        """Connect to server or to other client"""
        try:
            self.socket = socket.create_connection((ip,port))
        except:
            print(f"Could not connect to address {ip}:{port}")

    def disconnect(self):
        print("Closing socket")
        
        #Sends Empty message to indicate connection closing
        self.socket.sendmsg([bytes()])
        self.socket.close()

    def command_loop(self):
        """Reads User commands in a loop and sends then to connection."""
        while True:
            cmd = input(">").split(" ")
            print(cmd)

            if cmd[0] == "exit":
                break
            
            if cmd[0] == "adduser":
                self.socket.sendmsg([
                    bytes(cmd[0],"utf-8"),
                    bytes(";","utf-8"),
                    bytes(cmd[1],"utf-8"),
                ])

            
            for s in cmd:
                self.socket.sendmsg([bytes(s,'utf-8')])
