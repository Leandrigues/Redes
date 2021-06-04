import socket

class Client:
    """Classe que representa um Cliente"""
    
    def __init__(self):
        self.socket = None

    def start(self,port,ip):
        """Connects to server and reads user input."""

        self.connect(port,ip)
        self.command_loop()

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
            print("cmd: ",cmd)

            if cmd[0] == "exit":
                self.disconnect()
                break
            if cmd[0] == "adduser":
                self._send_adduser(cmd[1:])
                self._listen_adduserACK()

            elif cmd[0] == "login":
                self._send_login(cmd[1:])
                self._listen_loginACK()

            elif cmd[0] == "passwd":
                print(f"{cmd[0]} not implemented yet :(")

            elif cmd[0] == "begin":
                print(f"{cmd[0]} not implemented yet :(")

            elif cmd[0] == "send":
                print(f"{cmd[0]} not implemented yet :(")

            # Comandos que não tem argumentos
            elif cmd[0] in ["leaders","list","delay","end","logout"]:
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
            
            else:
                print("Command not recognized.")

    # Mensagens
    def _send_adduser(self, args):
        if len(args) < 2:
            print("adduser usage:\n"
                  "\tadduser <usuário> <senha>")
            return
        
        self.socket.sendmsg([
                bytes("adduser;","utf-8"),
                bytes(f"{args[0]};","utf-8"),
                bytes(f"{args[1]}","utf-8"),
            ])
    
    def _send_login(self, args):
        if len(args) < 2:
            print("login usage:\n"
                  "\tlogin <usuário> <senha>")
            return
        
        self.socket.sendmsg([
                bytes("login;","utf-8"),
                bytes(f"{args[0]};","utf-8"),
                bytes(f"{args[1]}","utf-8"),
            ])

    def _listen_loginACK(self):
        resp = str(self.socket.recv(1024)).split(";")
        if resp[0] == "loginACK":
            print("Login bem sucedido!")
        else:
            print(f"login failed, reason: {resp[1]}")

    def _listen_adduserACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        if resp[0] == "adduserACK":
            print("Usuário adicionado")
        else:
            print(f"adduser failed, reason: {resp[1]}")