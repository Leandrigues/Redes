import socket
from random import randint

from Jogo import Jogo

class Client:
    """Classe que representa um Cliente"""
    MYADDR="127.0.0.1"
    MATCHTIMEOUT=5

    def __init__(self):
        self.socket = None
        self.user_name = ''

    def start(self,port,ip):
        """Connects to server and reads user input."""

        self.socket = self.connect(port,ip)
        self.server_command_loop()

    def connect(self, port, ip, show_err = True) -> socket.socket:
        """Connect to server or to other client"""
        try:
            soc = socket.create_connection((ip,port))
        except Exception as e:
            print(f"Exception: {e}")
            print(f"Could not connect to address {ip}:{port}")
            soc = None

        return soc

    def disconnect(self):
        print("Closing socket")

        #Sends Empty message to indicate connection closing
        self.socket.sendmsg([bytes("exit", "utf-8")])
        self.socket.close()

    def server_command_loop(self):
        """Reads User commands in a loop and sends then to connection."""
        while True:
            self._listen_messages()
            cmd = input(">").split(" ")

            if not cmd: # Empty string
                continue
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
                if self._send_begin(cmd[1:]) is not None:
                    continue
                self._listen_beginACK()

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
            elif cmd[0] == "logout":
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                self._listen_logoutACK()

            elif cmd[0] in ["leaders","list","delay","end"]:
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")
                print(resp)

            else:
                print("Command not recognized.")

    def game_command_loop(self, soc : socket.socket, first_move=True):
        print("Entrou game_command_loop")

        self._my_simb = Jogo.SIMBOLOS[0 if first_move else 1]
        self._op_simb = Jogo.SIMBOLOS[1 if first_move else 0]

        # inicia tabuleiro
        jogo = Jogo()

        # Se não é o primeiro jogador, espera a primeira jogada.
        turns = 0 if first_move else 1
        print(jogo.tabuleiro)

        while jogo.terminou() is None:
            print("Loop it")
            if turns % 2: # turnos pares, minha jogada
                jogou = False
                while not jogou:
                    cmd = input(">").strip().split(" ")
                    if len(cmd) < 2:
                        print("Digite:\n> linha coluna")
                        continue
                    p_x, p_y = cmd
                    if jogo.pode_jogar(int(p_x), int(p_y)):
                        jogo.faz_jogada(int(p_x), int(p_y), self._my_simb)
                        self._send_play(p_x, p_y, soc)
                        jogou = True
                    else:
                        print("Posição inválida.")
            else:
                
                msg = soc.recv(1024).decode("utf-8")
                print("Jogada recebida: ", msg)
                p_x, p_y = msg.split(";")[1:]
                jogo.faz_jogada(int(p_x), int(p_y), self._op_simb)

            # fazer função de print para o jogo
            print(jogo.tabuleiro)
            turns += 1
        
        print("Saiu game_command_loop")
        

    def _bind_port(self, soc : socket.socket, port=3001) -> int:
        try:
            soc.bind((Client.MYADDR, port))
            print("Listening in port", port)
        except OSError:
            port += randint(1, 99)
            soc.bind((Client.MYADDR, port))
            print("Listening in port", port)

        return port


    def _get_match_socket(self):
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_port = self._bind_port(new_socket)
        return new_socket, new_port


    # Convites
    def _listen_messages(self):
        """Listen for unprompted server messages."""
        self.socket.settimeout(0.1)

        try:
            msg = self.socket.recv(1024)
        except socket.timeout as e:
            msg = None

        self.socket.settimeout(socket.getdefaulttimeout())

        print(f"Message: {msg}")
        if msg is not None:
            msg = msg.decode("utf-8").split(";")

            if msg[0] == "invite":
                #TODO: add validation here 
                user = msg[1]
                print(f"Received an invitation from: {user}")
                accept = input("Aceitar?\n[S/n]: ")
                if accept == "S":
                    print(f"Iniciando conexão com {user}")
                    self._match_socket, port = self._get_match_socket()

                    self.socket.sendmsg([
                        bytes(f"answer;{user};True;{port};{user}", "utf-8")
                    ])
                    print("Resposta enviada; Esperando conexão.")
                    self._match_socket.settimeout(Client.MATCHTIMEOUT)
                    try:
                        self._match_socket.listen()
                        conn, addr = self._match_socket.accept()
                    except socket.timeout as e:
                        conn = addr = None

                    if conn is None:
                        print("Conexão não foi recebida =(")
                    else:
                        print("Iniciando jogo!")
                        self.game_command_loop(conn)

                    # Se preparar para conexão
                else:
                    print(f"Recusando convite de {user}")
                    self.socket.sendmsg([
                        bytes(f"answer;{user};False", "utf-8")
                    ])

            elif msg[0] == "answer":
                user,accept = msg[1:3]
                if accept == "True":
                    print(f"User {user} has accepted your invite for a game :D")
                    print(msg)
                    addr,port = msg[3:5]
                    print(f"Connecting to user in {addr}:{port}")
                    conn = self.connect(port,addr,False)
                    self.game_command_loop(conn, False)
                else:
                    print(f"User {user} has declined your invite for a game =(")

            elif msg[0] == "disconnect":
                print("Received a disconnect message from server")
                self.socket.close()
                exit(1)

    # Mensagens
    def _send_play(self, p_x, p_y, soc):
        soc.sendmsg([bytes(
            f"play;{p_x};{p_y}", "utf-8")])

    def _send_begin(self, args):
        if len(args) < 1:
            print("begin usage:\n"
                  "\tbegin <usuário>")
            return

        self.socket.sendmsg([
                bytes("begin;","utf-8"),
                bytes(f"{args[0]};","utf-8"),
                bytes(f"{self.user_name}","utf-8"),
            ])

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

    # Respostas
    def _listen_beginACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        print(resp)
        if resp[0] == "beginACK":
            print("Begin bem sucedido!")
            # self.user_name = resp[1]
        else:
            print(f"begin failed, reason: {resp[1]}")

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
        print("Listen passACK:", resp)
        if resp[0] == "passwdACK":
            print("Senha alterada com sucesso.")
        else:
            print("Falha ao alterar senha. Motivo:", resp[1])

    def _listen_logoutACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        print(resp[0])

        if resp[0] == "logoutACK":
            self.user_name = ''
            print("Deslogado com sucesso!")
        else:
            print("Falha ao deslogar.")
