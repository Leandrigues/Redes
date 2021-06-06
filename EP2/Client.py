import socket

class Client:
    """Classe que representa um Cliente"""

    def __init__(self):
        self.socket = None
        self.user_name = 'leandro'

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
                if self._send_adduser(cmd[1:]) is not None:
                    continue
                self._listen_adduserACK()

            elif cmd[0] == "login":
                if self._send_login(cmd[1:]) is not None:
                    continue
                self._listen_loginACK()

            elif cmd[0] == "passwd":
                if self._send_passwd(cmd[1:]) is not None:
                    continue
                self._listen_passwdACK()

            elif cmd[0] == "begin":
                print(f"{cmd[0]} not implemented yet :(")
            elif cmd[0] == "send":
                print(f"{cmd[0]} not implemented yet :(")

            elif cmd[0] == "list":
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")

                print("-"*30 + 
                      "\nUsers currently logged in:\n" +
                      "-"*30)

                for u in resp.split(";")[1:]:
                    print(f"\t{u}")

            # Comandos que não tem argumentos
            elif cmd[0] in ["leaders","list","delay","end","logout"]:
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")
                print(resp)

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
            return 1

        self.socket.sendmsg([
                bytes("login;","utf-8"),
                bytes(f"{args[0]};","utf-8"),
                bytes(f"{args[1]}","utf-8"),
            ])

    def _send_passwd(self, args):
        if len(args) < 2:
            print("passwd <senha antiga> <senha nova>")
            return
        if self.user_name is None:
            print("Você precisa estar logado para alterar a senha.")
            return

        self.socket.sendmsg([
            bytes("passwd;", "utf-8"),
            bytes(f"{self.user_name};", "utf-8"),
            bytes(f"{args[0]};", "utf-8"),
            bytes(f"{args[1]}", "utf-8"),
        ])

    def _listen_loginACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        print(resp)
        if resp[0] == "loginACK":
            print("Login bem sucedido!")
            self.user_name = resp[1]
        else:
            print(f"login failed, reason: {resp[1]}")

    def _listen_adduserACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        if resp[0] == "adduserACK":
            print("Usuário adicionado")
        else:
            print(f"adduser failed, reason: {resp[1]}")

    def _listen_passwdACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        print("Listen passack:", resp)
        if resp[0] == "passwdACK":
            print("Senha alterada com sucesso.")
        else:
            print("Falha ao alterar senha. Motivo:", resp[1])