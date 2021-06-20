import socket
import threading
import sys
import signal
import os
from random import randint
from datetime import datetime
from ssl import SSLContext, PROTOCOL_TLS_SERVER

context = SSLContext(PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')

DEBUG=False

def _print(msg):
    if DEBUG:
        print(msg)

class Server:
    """
    Usuários já cadastrados ficam armazenados no arquivo users.txt, no
    formato (tab-separated):

    USERNAME    PASSWORD

    Cada conexão cria uma nova thread, que irá lidar com as necessidades desse cliente.

    Usuários logados ficam na lista Server.logged_users, que guarda tuplas:
        (username, socket)

    t_usernames, t_sockets, t_addresses são dicionários indexados pelo thread id da conexão.
    """
    HOST = "127.0.0.1"
    HOSTNAME="jogo-da-velha-server"
    USERSF = "users.txt"
    LOGF = "log.txt"
    logged_users = {}
    t_usernames = {}
    t_sockets = {}
    t_ssl_sockets = {}
    t_addresses = {}
    t_ssl_addresses = {}
    connections = []

    # user : (user, matched_user)
    current_matches = {}

    # Keeps matches that were only reported by a single user
    # (user1, user2) : winner
    reported_results = {}

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # force creation of user file
        open(Server.USERSF, "a+").close()
        open(Server.LOGF, "a+").close()

        # handles CTRL+C before exit
        signal.signal(signal.SIGINT, self._signal_handler)

    def listen(self, port):
        self._server_port = self._bind_port(port, self.socket)

        while True:
            self.socket.listen()
            conn, addr = self.socket.accept()
            self.connections.append(conn)
            self._write_log(f"Client connected from ip {addr[0]} and port {addr[1]}")
            threading.Thread(target=self._establish_connection, args=(conn, addr)).start()

    def _bind_port(self, port, soc, server=True):
        try:
            soc.bind((Server.HOST, int(port)))
        except OSError:
            port += randint(1, 99)
            soc.bind((Server.HOST, int(port)))

        if server:
            self._write_log(f"Server started listening in port {port}")

        print(f"Ouvindo na porta {port}")

        return port


    def _signal_handler(self, sig, frame):
        print("Server finalizando por receber CTRL+C")
        self._write_log(f"Server shutting down")
        self.disconnect_connected_clients()
        self.disconnect()
        os._exit(0)

    def disconnect_connected_clients(self):
        for conn in self.connections:
            _print(f"Desconectado {conn}")
            conn.sendmsg([bytes("disconnect", "utf-8")])

    def _establish_connection(self, conn, addr):
        # adds connection reference
        self.set_socket(conn)
        _print(f"conn: {conn}")
        self.set_addr(addr)

        _print(f"Conexão recebida de {addr}")

        #Setup secure connection
        ssoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        p = self._bind_port(self._server_port+1, ssoc, False)

        # Await for client to connect through ssl
        conn.sendmsg([bytes(f"secport;{p}","utf-8")])
        ssoc.listen()
        with context.wrap_socket(ssoc, server_side=True) as tls:
            sconn, saddr = tls.accept()
            self.set_ssl_socket(sconn)
            self.set_ssl_addr(saddr)

            sconn.settimeout(0.5)
            conn.settimeout(0.5)
            self._read_commands(conn, addr, sconn, saddr)

    def start_heartbeat(self, socket):
        if self.send_ping(socket) is None:
            self._write_log(f"Client in socket {socket} disconnected. Verified by heatbeat")
            return
        socket.settimeout(3)
        try:
            data = socket.recv(1024).decode("utf-8")
            if data != "pong":
                _print(f"Socket {socket} não está respondendo")
                self._write_log(f"Client in socket {socket} disconnected. Verified by heatbeat")
                return
        except Exception as e:
            _print(f"Socket {socket} não está respondendo")
            self._write_log(f"Client in socket {socket} disconnected. Verified by heatbeat")
            socket.close()


        threading.Timer(10, self.start_heartbeat, args=(socket,)).start()

    def send_ping(self, socket):
        try:
            socket.sendmsg([bytes("ping", "utf-8")])
            return "ok"
        except BrokenPipeError as e:
            return


    def start_ping_socket(self, port):
        try:
            ping_socket = socket.create_connection((self.HOST, port))
        except Exception as e:
            _print(f"Exception: {e}")
            _print(f"Não foi possível conectar-se a {self.HOST}:{port}")

        self.start_heartbeat(ping_socket)

    def start_communication(self, conn):
        # Defines ping port
        data = conn.recv(1024).decode("utf-8").split(';')
        ping_port = data[0]
        _print(f"Porta do socket de heatbeat será {ping_port}")
        threading.Thread(target=self.start_ping_socket, args=(ping_port,)).start()

    def _read_commands(self, conn, addr, sconn, saddr):
        self.start_communication(conn)

        # main loop
        while True:

            sconn_timeout = False
            conn_timeout = False
            try:
                data = sconn.recv(1024)
            except socket.timeout as e:
                sconn_timeout = True

            try:
                data = conn.recv(1024)

            except socket.timeout as e:
                conn_timeout = True

            if conn_timeout and sconn_timeout:
                continue

            if not data:
                break

            _print(f"Data: {data}")
            msg = data.decode("utf-8").split(";")
            _print(f"Comando: {msg}")

            if msg[0] == "adduser":
                resp = self._adduser(msg[1:])
                r_soc = sconn
            elif msg[0] == "passwd":
                resp = self._passwd(msg[1:])
                r_soc = sconn
            elif msg[0] == "login":
                resp = self._login(msg[1:], addr)
                r_soc = sconn
            elif msg[0] == "list":
                resp = self._list()
                r_soc = conn
            elif msg[0] == "leaders":
                resp = self._leaders()
                r_soc = conn
            elif msg[0] == "begin":
                resp = self._begin(msg[1:])
                r_soc = conn
            elif msg[0] == "answer":
                resp = self._answer(msg[1:])
                r_soc = conn
            elif msg[0] == "result":
                resp = self._result(msg[1:])
                r_soc = conn
            elif msg[0] == "exit":
                resp = self.disconnect_user(addr)
                break
            elif msg[0] == "logout":
                resp = self.logout_user()
                r_soc = sconn
            else:
                resp = ['Comando Não Reconhecido']
                r_soc = conn
            _print(f"resp:{resp}")
            r_soc.sendall(bytes(";".join(resp),"utf-8"))

    # Message related methods
    def disconnect_user(self, addr):
        self._write_log(f"User from ip {addr[1]} disconnected")
        return ["exitACK"]

    def disconnect(self):
        _print("Fechando socket")
        self.socket.close()

    def log_user(self, username):
        _print(f"Usuário {username} logando")
        Server.logged_users[username] = self.get_socket()

    def logout_user(self):
        _print(f"Deslogando {self.get_uname()}")
        del Server.logged_users[self.get_uname()]
        return ["logoutACK"]


    def invite_user(self, u_socket, sender):
        _print(f"Convidando {u_socket} para conexão")
        u_socket.sendmsg([bytes(f"invite;{sender}","utf-8")])

    def answer_user(self, u_socket, accept, sender_name, ping_port, sender_port=None):
        _print(f"Respondendo usuário no socket: {u_socket}")
        receiver_name = self.get_uname()
        receiver_conn = Server.logged_users[receiver_name].getpeername()
        sender_conn = Server.logged_users[sender_name].getpeername()

        answer_string = f"answer;{self.get_uname()};{accept}"
        if accept:
            self._write_log(f"A game was started between {receiver_name} {receiver_conn} and {sender_name} {sender_conn}")
            answer_string += f";{self.get_addr()[0]};{sender_port};{ping_port}"
            self.current_matches[sender_name] = self.get_uname()
            self.current_matches[self.get_uname()] = sender_name


        u_socket.sendmsg([bytes(answer_string,"utf-8")])

    def _answer(self, args):
        """Relays answer to game invitation"""
        if len(args) < 2:
            _print("answer precisa de 2 argumentos")
            return ["answerERR", "Wrong Number of Arguments"]

        user_to_answer, accept = args[:2]
        if len(args) > 2:
            sender_port, sender_user_name, ping_port = args[2:]
        else:
            sender_port = sender_user_name = ping_port = None

        _print("Usernames:", Server.logged_users)
        if user_to_answer in Server.logged_users:
            self.answer_user(Server.logged_users[user_to_answer], accept, sender_user_name, ping_port, sender_port)
            return ["answerACK"]

        return ["answerERR", "User not connected, can't respond"]

    def _begin(self, args):
        """Invites another user and waits for response."""
        if len(args) != 2:
            _print("Begin precisa de 2 argumentos")
            return ["beginERR", "Wrong Number of Arguments"]

        invited_user = args[0]
        sender_user = args[1]

        if Server.current_matches.get(sender_user) is not None:
            return ["beginERR", "Inviting User currently in a match"]

        _print(f"{sender_user} está convidando {invited_user}")
        if invited_user in Server.logged_users:
            if Server.current_matches.get(invited_user) is not None:
                return ["beginERR", "Invited user currently in a match"]

            self.invite_user(Server.logged_users[invited_user], sender_user)
            return ["beginACK"]

        return ["beginERR", "Invited user not connected"]

        #invite_successfull = self.invite_user(invited_user)

    def _list(self):
        return ["listACK"] + [u for u in Server.logged_users]

    def _leaders(self):
        resp = ["leadersACK"]
        with open(Server.USERSF, "r") as handle:
            for line in handle.readlines():
                username, _, score = line.strip().split("\t")
                resp.append(f"{username}:{score}")
        _print(f"Resp: {resp}")
        return resp

    def _login(self, args, addr):
        if len(args) != 2:
            _print("login precisa de 2 argumentos")
            return ["loginERR", "Wrong Number of Arguments"]

        username, passwd = args
        with open(Server.USERSF, "r") as handle:
            users = handle.read().split("\n")
            for user in users:
                if user == "":
                    break
                current_username, current_password, _ = user.split("\t")
                if username == current_username:
                    if passwd == current_password:
                        # TODO: check if user is alreaddy logged in
                        self.log_user(username)

                        #TODO: check if this connection is already logged in
                        self.set_uname(username)
                        self._write_log(f"User '{username}' successfuly logged in from ip {addr[0]}")
                        return ["loginACK", username]
                    else:
                        self._write_log(f"User '{username}' failed to login from ip {addr[0]}")
                        return ["loginERR", "Wrong Password"]

            return ["loginERR", "Username not found"]

    def _adduser(self, args):
        if len(args) != 2:
            _print("adduser precisa de 2 argumentos")
            return ["adduserERR", "Wrong Number of Arguments"]

        new_username = args[0]
        with open(Server.USERSF, "r") as handle:
            # Lê todos os usuários para a memória pq fazer a inserção no
            # arquivo em si é muito trampo

            users = handle.readlines()

        user_names = []
        for entry in users:
            user_names.append(entry.split('\t')[0])

        if new_username in user_names:
            _print("Usuário já cadastrado.\n")
            return ["adduserERR", "USEREXISTS"]

        users.append("\t".join(args) + '\t0\n')
        user_it = iter(users)


        # Sobrescreve arquivo
        with open(Server.USERSF,"w") as handle:
            handle.writelines(sorted(users))
            handle.close()
        return ["adduserACK"]

    def _passwd(self, args):
        if len(args) != 3:
            _print("passwd precisa de 3 argumentos")
            return ["passwdERR", "Wrong Number of Arguments"]

        user, old_password, new_password = msg

        if old_password == new_password:
            return ["passwdERR", "SAMEPASSWORD"]

        with open(Server.USERSF,"r") as file:
            lines = file.readlines()

        for index, line in enumerate(lines):
            line_array = line.replace('\n', '').split("\t")

            if line_array[0] == user:
                if line_array[1] != old_password:
                    return ["passwdERR", "WRONGPASSWORD"]
                else:
                    new_line = f"{user}\t{new_password}\t{line_array[2]}\n"
                    lines[index] = new_line
                    break

        with open(Server.USERSF, "w") as file:
            file.writelines(lines)

        return ["passwdACK"]

    def _result(self, args):
        if len(args) < 3:
            return ["resultERR","Wrong Number of Arguments"]

        user1, user2, user1_win = args
        winner = user1 if user1_win == "WIN" else user2
        reported_winner = Server.reported_results.get((user1,user2))
        if reported_winner is None:
            Server.reported_results[(user1,user2)] = winner
            Server.reported_results[(user2,user1)] = winner
            return ["resultACK"]

        if reported_winner == winner:
            del Server.reported_results[(user2,user1)]
            del Server.reported_results[(user1,user2)]
            self._increase_score(winner)
            return ["resultACK"]

        # Users disagree with result

        other_user = user1 if user2 == self.get_uname() else user2

        # tries to contact other user as well
        if other_user in Server.logged_users:
            soc = Server.logged_users[other_user].getpeername()
            soc.sendall(bytes(
                f"resultERR;Conflicting reports of match result with {self.get_uname()}",
                "utf-8"))

        return ["resultERR","Conflicting reports of match result"]
    # util methods:

    def _increase_score(self, username):
        with open(Server.USERSF) as handle:
            lines = handle.readlines()

        for index, line in enumerate(lines):
            line_array = line.replace('\n', '').split("\t")

            if line_array[0] == username:
                    new_line = f"{username}\t{line_array[1]}\t{int(line_array[2])+1}\n"
                    lines[index] = new_line
                    break

        with open(Server.USERSF, "w") as file:
            file.writelines(lines)

    def _get_formated_time(self):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

    def get_uname(self):
        """Returns current thread associated Username or None"""
        return Server.t_usernames.get(threading.get_ident())

    def set_uname(self, username):
        """Sets username associated with current thread"""
        Server.t_usernames[threading.get_ident()] = username
        _print(f"t_usernames: {Server.t_usernames}")

    def get_socket(self):
        """Returns current thread associated socket or None"""
        _print(f"THREADING IDENT: {threading.get_ident()}")
        return Server.t_sockets.get(threading.get_ident())

    def set_socket(self, socket):
        """Sets socket associated with current thread"""
        Server.t_sockets[threading.get_ident()] = socket

    def get_addr(self):
        """Returns current address associated socket or None"""
        return Server.t_addresses.get(threading.get_ident())

    def set_addr(self, addr):
        """Sets address associated with current thread"""
        Server.t_addresses[threading.get_ident()] = addr

    def get_ssl_socket(self):
        """Returns current thread associated ssl socket or None"""
        _print(f"THREADING IDENT: {threading.get_ident()}")
        return Server.t_ssl_sockets.get(threading.get_ident())

    def set_ssl_socket(self, socket):
        """Sets ssl socket associated with current thread"""
        Server.t_ssl_sockets[threading.get_ident()] = socket

    def get_ssl_addr(self):
        """Returns current address associated ssl socket or None"""
        return Server.t_ssl_addresses.get(threading.get_ident())

    def set_ssl_addr(self, addr):
        """Sets ssl address associated with current thread"""
        Server.t_ssl_addresses[threading.get_ident()] = addr

    def _write_log(self, log):
        with open(Server.LOGF, "a") as f:
            f.write(f"{self._get_formated_time()} {log}\n")
            f.close()
