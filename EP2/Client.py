import socket
import time
import threading
import signal
from random import randint
from Jogo import Jogo
from ssl import SSLContext, PROTOCOL_TLS_CLIENT

context = SSLContext(PROTOCOL_TLS_CLIENT)
context.load_verify_locations('cert.pem')

DEBUG=False

def _print(msg):
    if DEBUG:
        print(msg)

class Client:
    """Classe que representa um Cliente"""
    MYADDR="127.0.0.1"
    MATCHTIMEOUT=5

    def __init__(self):
        self.socket = None
        self.user_name = ''
        self.delays = []
        self.buffer = None

    def start(self,port,ip):
        """Connects to server and reads user input."""

        hostname="jogo-da-velha-server"
        self.socket = self.connect(port,ip)
        th = threading.Thread(target=self.start_ping)
        th.daemon = True
        th.start()
        self.server_ip = ip
        self.server_port = port
        # await for secure port
        signal.signal(signal.SIGINT, self._signal_handler)

        self.s_port = int(self.socket.recv(100).decode("utf-8").split(";")[1])
        ssoc = self.connect(self.s_port,ip)
        with context.wrap_socket(ssoc, server_hostname=hostname) as tls:
            self.server_command_loop(self.socket, tls)

    def _signal_handler(self, sig, frame):
        print("Finalizando cliente")
        self.socket.sendmsg([bytes("exit", "utf-8")])
        self.socket.close()
        exit(0)

    def start_ping(self):
        _print("Iniciando socket de ping")
        self.ping_socket, self.ping_port = self._get_socket(8080)
        try:
            self.ping_socket.listen()
            self.conn_ping, addr_ping = self.ping_socket.accept()
            _print(f"Conexão com o socket feita: {self.conn_ping}")
        except socket.timeout as e:
            _print(e)
        self._read_heartbeat(self.conn_ping)

    def _read_heartbeat(self, soc):
        while True:
            data = soc.recv(1024).decode("utf-8")
            if data == "ping":
                soc.sendmsg([bytes("pong", "utf-8")])


    def connect(self, port, ip, show_err = True) -> socket.socket:
        """Connect to server or to other client"""
        try:
            soc = socket.create_connection((ip,port))
        except Exception as e:
            if show_err:
                _print(f"Exception: {e}")
                _print(f"Não foi possível de conectar a {ip}:{port}")
            soc = None

        return soc

    def disconnect(self):
        _print("Closing socket")

        #Sends Empty message to indicate connection closing
        self.socket.sendmsg([bytes("exit", "utf-8")])
        self.socket.close()

    def start_communication(self):
        self.socket.sendmsg([bytes(f"{self.ping_port}", "utf-8")])

    def server_command_loop(self, soc, ssoc):
        """Reads User commands in a loop and sends then to connection."""
        self.start_communication()
        while True:
            self._listen_messages()
            cmd = input(">").split(" ")

            if not cmd[0]: # Empty string
                continue
            _print(f"cmd: {cmd}")

            if cmd[0] == "exit":
                self.disconnect()
                break
            if cmd[0] == "adduser":
                if self._send_adduser(cmd[1:], ssoc) is not None:
                    continue
                self._listen_adduserACK(ssoc)

            elif cmd[0] == "login":
                if self._send_login(cmd[1:], ssoc) is not None:
                    continue
                self._listen_loginACK(ssoc)

            elif cmd[0] == "passwd":
                if self._send_passwd(cmd[1:], ssoc) is not None:
                    continue
                self._listen_passwdACK(ssoc)

            elif cmd[0] == "begin":
                if self._send_begin(cmd[1:]) is not None:
                    continue
                self._listen_beginACK()

            elif cmd[0] == "list":
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")

                print("-"*30 + 
                      "\nUsuários conectados:\n" +
                      "-"*30)

                for u in resp.split(";")[1:]:
                    print(f"\t{u}")

            elif cmd[0] == "leaders":
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")

                leaderboard = [[s for s in u.split(":")] for u in resp.split(";")[1:]]
                leaderboard.sort(key=lambda x: int(x[1]),reverse=True)

                print("-"*21 + 
                      f"\n{'LEADERBOARD':^20}\n" +
                      "-"*21)

                for username, score in leaderboard:
                    print(f"{username:^12}|  {int(score):3d}  |")

            elif cmd[0] in ["end"]:
                self.socket.sendmsg([bytes(cmd[0],"utf-8")])
                resp = self.socket.recv(1024).decode("utf-8")
                print(resp)

            else:
                print("Comando não reconhecido")

    def _handle_ingame_comands(self, soc):
        while True:
            cmd = input(">").strip().split(" ")
            if cmd[0] == "send":
                if len(cmd) < 3:
                    return ["send"]
                return ["send", cmd[1], cmd[2]]

            if cmd[0] == "delay":
                size = len(self.delays)
                delays = ', '.join(self.delays[-3:])
                print(f"Últimas latências medidas: {delays}")
                return ["delay"]
            else:
                print("Comando não reconhecido")

    def _send_ping(self, soc):
        soc.sendmsg([bytes("ping", "utf-8")])

    def _send_pong(sef, soc):
        soc.sendmsg([bytes("pong", "utf-8")])

    def _get_delay(self, soc):
        self._send_ping(soc)
        before = time.time()
        while True:
            if self.buffer is not None and self.buffer == "pong":
                self.buffer = None
                after = time.time()
                self.delays.append(str(float(after) - float(before)))
                break

        threading.Timer(3, self._get_delay, args=(soc,)).start()


    def _read_pings(self, soc):
        while True:
            data = soc.recv(1024).decode("utf-8")
            if data == "ping":
                _print("Ping recebido")
                soc.sendmsg([bytes("pong", "utf-8")])
            elif data == "pong":
                _print("Pong recebido")
                self.buffer = "pong"
            else:
                _print(f"Dado inesperado: {data}")
                _print("Fechando conexão")
                soc.close()


    def game_command_loop(self, soc : socket.socket, ping_socket, opponent:str, first_move=True):
        _print("Entrou game_command_loop")

        self._my_simb = Jogo.SIMBOLOS[0 if first_move else 1]
        self._op_simb = Jogo.SIMBOLOS[1 if first_move else 0]

        # inicia tabuleiro
        jogo = Jogo()

        # Inicia a medição periódica de latência
        th1 = threading.Thread(target=self._read_pings, args=(ping_socket,))
        th1.daemon = True
        th1.start()
        th2 = threading.Thread(target=self._get_delay, args=(ping_socket,))
        th2.daemon = True
        th2.start()

        # Se não é o primeiro jogador, espera a primeira jogada.
        turns = 0 if first_move else 1

        print("\n"*10+"Jogo iniciado!")
        print(jogo)

        while jogo.terminou() is None:
            if turns % 2: # turnos pares, minha jogada
                jogou = False
                while not jogou:
                    cmd = self._handle_ingame_comands(soc)
                    if cmd[0] != "send":
                        continue
                    if len(cmd) < 2:
                        print("Digite:\n> send linha coluna")
                        continue
                    p_x, p_y = cmd[1:]
                    if jogo.pode_jogar(int(p_x), int(p_y)):
                        jogo.faz_jogada(int(p_x), int(p_y), self._my_simb)
                        self._send_play(p_x, p_y, soc)
                        jogou = True
                    else:
                        print("Posição inválida.")
            else:
                msg = soc.recv(1024).decode("utf-8").split(";")[1:]

                if len(msg) < 2:
                    self._send_pong(soc)
                    continue

                _print(f"Jogada recebida: {msg}")
                p_x, p_y = msg
                jogo.faz_jogada(int(p_x), int(p_y), self._op_simb)

            # fazer função de _print para o jogo
            print(jogo)
            turns += 1

        if jogo.terminou() != self._my_simb:
            print(f"Você perdeu o jogo contra {opponent}! X(")
            self.socket.sendmsg([bytes(f"result;{self.user_name};{opponent};LOST","utf-8")])
        else:
            print(f"Você ganhou o jogo contra {opponent}! :D")
            self.socket.sendmsg([bytes(f"result;{self.user_name};{opponent};WIN","utf-8")])

        self._listen_resultACK()
        _print("Saiu game_command_loop")

    def _bind_port(self, soc : socket.socket, port=3001) -> int:
        try:
            soc.bind((Client.MYADDR, port))
            _print(f"Ouvindo na porta {port}")
        except OSError:
            port += randint(1, 99)
            soc.bind((Client.MYADDR, port))
            _print(f"Ouvindo na porta {port}")

        return port


    def _get_socket(self, port=3002):
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_port = self._bind_port(new_socket, port)
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

        _print(f"Message: {msg}")
        if msg is not None:
            msg = msg.decode("utf-8").split(";")

            if msg[0] == "invite":
                # TODO: add validation here
                user = msg[1]
                print(f"{user} te convidou para jogar!")
                accept = input("Aceitar?\n[S/n]: ")
                if accept == "S":
                    _print(f"Iniciando conexão com {user}")
                    self._match_socket, match_port = self._get_socket()
                    self._ping_socket, ping_port = self._get_socket(3099)
                    _print(f"PING SOCKET: {self._ping_socket}")
                    self.socket.sendmsg([
                        bytes(f"answer;{user};True;{match_port};{self.user_name};{ping_port}", "utf-8")
                    ])
                    print("Resposta enviada; Esperando conexão.")

                    if self._listen_answerACK() is not None:
                        return

                    self._match_socket.settimeout(Client.MATCHTIMEOUT)
                    try:
                        self._match_socket.listen()
                        conn_match, addr = self._match_socket.accept()
                    except socket.timeout as e:
                        conn_match = addr = None
                        _print(e)

                    if conn_match is None:
                        _print("Conexão não foi recebida =(")
                        raise Exception

                    # self._ping_socket.settimeout(Client.MATCHTIMEOUT)
                    try:
                        self._ping_socket.listen()
                        conn_ping, addr_ping = self._ping_socket.accept()
                        _print(f"Conexão com ping aceita: {conn_ping}")
                    except socket.timeout as e:
                        # raise e
                        _print(e)

                    print("Iniciando jogo!")
                    self.game_command_loop(conn_match, conn_ping, user)

                else:
                    print(f"Convite de {user} recusado.")
                    self.socket.sendmsg([
                        bytes(f"answer;{user};False", "utf-8")
                    ])

            elif msg[0] == "answer":
                user,accept = msg[1:3]
                if accept == "True":
                    print(f"{user} aceitou seu convite para jogar :D")
                    _print(msg)
                    addr, match_port, ping_port = msg[3:6]
                    _print(f"Conectando com usuário em {addr}:{match_port}")
                    conn_match = self.connect(match_port, addr, False)
                    conn_ping = self.connect(ping_port, addr, True)

                    # Retry until it connects
                    while conn_match is None:
                        conn_match = self.connect(match_port, addr, False)
                    while conn_ping is None:
                        conn_ping = self.connect(ping_port, addr, False)

                    self.game_command_loop(conn_match, conn_ping, user, False)
                else:
                    print(f"{user} recusou seu convite =(")

            elif msg[0] == "disconnect":
                _print("Mensagem de desconexão recebida do servidor.")
                self.socket.close()
                exit(1)

    # Mensagens
    def _send_play(self, p_x, p_y, soc):
        soc.sendmsg([bytes(
            f"play;{p_x};{p_y}", "utf-8")])

    def _send_begin(self, args):
        if len(args) < 1:
            print("begin:\n"
                  "\tbegin <usuário>")
            return

        self.socket.sendmsg([
                bytes("begin;","utf-8"),
                bytes(f"{args[0]};","utf-8"),
                bytes(f"{self.user_name}","utf-8"),
            ])

    def _send_adduser(self, args, soc):
        if len(args) < 2:
            print("adduser:\n"
                  "\tadduser <usuário> <senha>")
            return

        soc.sendall(bytes(f"adduser;{args[0]};{args[1]}","utf-8"))

    def _send_login(self, args, soc):
        if len(args) < 2:
            print("login:\n"
                  "\tlogin <usuário> <senha>")
            return 1

        soc.sendall(
                bytes(f"login;{args[0]};{args[1]}","utf-8"),
            )

    def _send_passwd(self, args, soc):
        if len(args) < 2:
            print("passwd <senha antiga> <senha nova>")
            return
        if self.user_name is None:
            print("Você precisa estar logado para alterar a senha.")
            return

        soc.sendall(
            bytes(f"passwd;{self.user_name};{args[0]};{args[1]}", "utf-8"),
        )

    # Respostas
    def _listen_beginACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        _print(resp)
        if resp[0] == "beginACK":
            print("Begin bem sucedido!")
        else:
            print(f"begin falhou, motivo: {resp[1]}")

    def _listen_answerACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        _print(resp)
        if resp[0] == "answerACK":
            _print("Answer bem sucedido!")
            return
        else:
            _print(f"answer falhou, motivo: {resp[1]}")
            return 1


    def _listen_loginACK(self, soc):
        resp = soc.recv(1024).decode("utf-8").split(";")
        _print(resp)
        if resp[0] == "loginACK":
            print("Login bem sucedido!")
            self.user_name = resp[1]
        else:
            print(f"login falhou, motivo: {resp[1]}")

    def _listen_adduserACK(self, soc):
        resp = soc.recv(1024).decode("utf-8").split(";")
        if resp[0] == "adduserACK":
            print("Usuário adicionado")
        else:
            print(f"adduser falhou com a mensagem:{resp[1]}")

    def _listen_passwdACK(self, soc):
        resp = soc.recv(1024).decode("utf-8").split(";")
        _print(f"Listen passwdACK: {resp}")
        if resp[0] == "passwdACK":
            print("Senha alterada com sucesso.")
        else:
            print(f"passwd falhou, motivo: {resp[1]}")

    def _listen_resultACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        _print(f"Listen resultACK: {resp}")
        if resp[0] == "resultACK":
            print("Resultado reportado com sucesso.")
        else:
            print(f"Falha ao reportar resultado, motivo: {resp[1]}")

    def _listen_logoutACK(self):
        resp = self.socket.recv(1024).decode("utf-8").split(";")
        _print(resp[0])

        if resp[0] == "logoutACK":
            self.user_name = ''
            print("Deslogado com sucesso!")
        else:
            print("Falha ao deslogar.")
