import socket
from random import randint
import threading

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
    logged_users = {}
    t_usernames = {}
    t_sockets = {}
    t_addresses = {}

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # force creation of user file
        open(Server.USERSF,"w").close()

    def listen(self, port):
        self._bind_port(port)

        while True:
            self.socket.listen()
            conn, addr = self.socket.accept()
            client_thread = threading.Thread(target=self._read_commands, args=(conn, addr))
            client_thread.start()

        self.disconnect()

    def _bind_port(self, port):
        try:
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)
        except OSError:
            port += randint(1, 99)
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)

    def _read_commands(self, conn, addr):
        # local connection data

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
                resp = self._login(msg[1:])
            elif msg[0] == "list":
                resp = self._list()
            elif msg[0] == "begin":
                resp = self._begin(msg[1:])
            elif msg[0] == "answer":
                resp = self._answer(msg[1:])
            else:
                resp = ['Comando Não Reconhecido']
            print(resp)
            conn.sendmsg([bytes(";".join(resp),"utf-8")])


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
        """Returns current thread associated socket or None"""
        return Server.t_addresses.get(threading.get_ident())

    def set_addr(self, addr):
        """Sets socket associated with current thread"""
        Server.t_addresses[threading.get_ident()] = addr


    # Message related methods

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

    def answer_user(self, u_socket, accept):
        print(f"Answering user in connection: {u_socket}")
        u_socket.sendmsg([
            bytes(f"answer;{self.get_uname()};{accept}","utf-8")])

    def _answer(self, args):
        """Relays answer to game invitation"""
        if len(args) != 2:
            print("answer requires 2 arguments")
            return ["answerERR", "Wrong Number of Arguments"]

        ans_user, accept = args
        print("USERNAMES:", Server.logged_users)
        if ans_user in Server.logged_users:
            self.answer_user(Server.logged_users[ans_user], accept)
            return ["answerACK"]

        return ["answerERR", "User not connected, can't respond"]

    def _begin(self, args):
        """Invites another user and waits for response."""
        if len(args) != 2:
            print("begin requires 1 argument")
            return ["beginERR", "Wrong Number of Arguments"]

        invited_user = args[0]
        sender = args[1]
        print(f"{sender} is inviting {invited_user}")
        if invited_user in Server.logged_users:
            self.invite_user(Server.logged_users[invited_user], sender)
            return ["beginACK"]

        return ["beginERR", "Invited user not connected"]

        #invite_successfull = self.invite_user(invited_user)

    def _list(self):
        return ["listACK"] + [u for u,_ in Server.logged_users]

    def _login(self, args):
        if len(args) != 2:
            print("login requires 2 arguments")
            return ["loginERR", "Wrong Number of Arguments"]

        username,passwd = args
        with open(Server.USERSF, "r") as handle:
            users = handle.read().split("\n")
            for u in users:
                cur_usn, cur_pswd = u.split("\t")
                if username == cur_usn:
                    if passwd == cur_pswd:
                        # TODO: check if user is alreaddy logged in
                        self.log_user(username)

                        #TODO: check if this connection is already logged in
                        self.set_uname(username)
                        return ["loginACK", username]
                    else:
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

