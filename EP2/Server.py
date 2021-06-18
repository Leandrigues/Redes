import socket
import threading
import sys
import signal
import os
from random import randint
from datetime import datetime

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
    USERSF = "users.txt"
    LOGF = "log.txt"
    logged_users = {}
    t_usernames = {}
    t_sockets = {}
    t_addresses = {}
    connections = []

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # force creation of user file
        open(Server.USERSF, "a+").close()
        open(Server.LOGF, "a+").close()

        # handles CTRL+C before exit
        signal.signal(signal.SIGINT, self._signal_handler)

    def listen(self, port):
        self._bind_port(port)

        while True:
            self.socket.listen()
            conn, addr = self.socket.accept()
            self.connections.append(conn)
            self._write_log(f"Client connected from ip {addr[0]} and port {addr[1]}")
            client_thread = threading.Thread(target=self._read_commands, args=(conn, addr))
            client_thread.start()


    def _bind_port(self, port):
        try:
            self.socket.bind((Server.HOST, port))
        except OSError:
            port += randint(1, 99)
            self.socket.bind((Server.HOST, port))

        print("Listening in port", port)


        self._write_log(f"Server started listening in port {port}")


    def _signal_handler(self, sig, frame):
        print("Received a CTRL+C")
        self._write_log(f"Server shutting down")
        self.disconnect_connected_clients()
        self.disconnect()
        os._exit(0)


    def disconnect_connected_clients(self):
        for conn in self.connections:
            print(f"Disconnecting {conn}")
            conn.sendmsg([bytes("disconnect", "utf-8")])

    def _read_commands(self, conn, addr):
        # adds connection reference
        self.set_socket(conn)
        print(f"conn: {conn}")
        self.set_addr(addr)

        # main loop
        while True:
            print("Received connection from", addr)
            print("LOGGED: ", self.logged_users)
            data = conn.recv(1024)
            if not data:
                break

            print(f"Received: {data}")
            msg = data.decode("utf-8").split(";")
            print(f"Command: {msg}")

            if msg[0] == "adduser":
                resp = self._adduser(msg[1:])
            elif msg[0] == "passwd":
                resp = self._passwd(msg[1:])
            elif msg[0] == "login":
                resp = self._login(msg[1:], addr)
            elif msg[0] == "list":
                resp = self._list()
            elif msg[0] == "begin":
                resp = self._begin(msg[1:])
            elif msg[0] == "answer":
                resp = self._answer(msg[1:])
            elif msg[0] == "exit":
                resp = self.disconnect_user(addr)
                break
            else:
                resp = ['Comando Não Reconhecido']
            print(resp)
            conn.sendmsg([bytes(";".join(resp),"utf-8")])

    # Message related methods
    def disconnect_user(self, addr):
        self._write_log(f"User from ip {addr[1]} disconnected")
        return ["exitACK"]

    def disconnect(self):
        print("Closing socket")
        self.socket.close()

    def log_user(self, username):
        print(f"Login in user: {username}")
        Server.logged_users[username] = self.get_socket()

    def logout_user(self, username):
        print(f"Login out user: {username}")
        del Server.logged_users[username]

    def invite_user(self, u_socket, sender):
        print(f"inviting user in connection: {u_socket}")
        u_socket.sendmsg([bytes(f"invite;{sender}","utf-8")])

    def answer_user(self, u_socket, accept, sender_port=None):
        print(f"Answering user in connection: {u_socket}")

        answer_string = f"answer;{self.get_uname()};{accept}"
        if accept: 
            answer_string += f";{self.get_addr()[0]};{sender_port}"

        u_socket.sendmsg([bytes(answer_string,"utf-8")])

    def _answer(self, args):
        """Relays answer to game invitation"""
        if len(args) < 2:
            print("answer requires at least 2 arguments")
            return ["answerERR", "Wrong Number of Arguments"]

        user_to_answer, accept = args[:2]
        sender_port = args[2] if len(args) > 2 else None
        print("USERNAMES:", Server.logged_users)
        if user_to_answer in Server.logged_users:
            self.answer_user(Server.logged_users[user_to_answer], accept, sender_port)
            return ["answerACK"]

        return ["answerERR", "User not connected, can't respond"]

    def _begin(self, args):
        """Invites another user and waits for response."""
        if len(args) != 2:
            print("begin requires 1 argument")
            return ["beginERR", "Wrong Number of Arguments"]

        invited_user = args[0]
        sender_user = args[1]
        print(f"{sender_user} is inviting {invited_user}")
        if invited_user in Server.logged_users:
            self.invite_user(Server.logged_users[invited_user], sender_user)
            return ["beginACK"]

        return ["beginERR", "Invited user not connected"]

        #invite_successfull = self.invite_user(invited_user)

    def _list(self):
        return ["listACK"] + [u for u in Server.logged_users]

    def _login(self, args, addr):
        if len(args) != 2:
            print("login requires 2 arguments")
            return ["loginERR", "Wrong Number of Arguments"]

        username, passwd = args
        with open(Server.USERSF, "r") as handle:
            users = handle.read().split("\n")
            for user in users:
                if user == "":
                    break
                current_username, current_password = user.split("\t")
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
            print("adduser requires 2 arguments")
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
            print("Usuário já cadastrado.\n")
            return ["adduserERR", "USEREXISTS"]

        users.append("\t".join(args) + '\n')
        user_it = iter(users)


        # Sobrescreve arquivo
        with open(Server.USERSF,"w") as handle:
            handle.writelines(sorted(users))
            handle.close()
        return ["adduserACK"]

    def _passwd(self, args):
        if len(args) != 3:
            print("passwd requires 3 arguments")
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
                    new_line = f"{user}\t{new_password}\n"
                    lines[index] = new_line
                    break

        with open(Server.USERSF, "w") as file:
            file.writelines(lines)

        return ["passwdACK"]

    def _get_formated_time(self):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

    # util methods:

    def get_uname(self):
        """Returns current thread associated Username or None"""
        return Server.t_usernames.get(threading.get_ident())

    def set_uname(self, username):
        """Sets username associated with current thread"""
        Server.t_usernames[threading.get_ident()] = username
        print(f"t_usernames:", Server.t_usernames)

    def get_socket(self):
        """Returns current thread associated socket or None"""
        print("THREADING IDENT:", threading.get_ident())
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

    def _write_log(self, log):
        with open(Server.LOGF, "a") as f:
            f.write(f"{self._get_formated_time()} {log}\n")
            f.close()
