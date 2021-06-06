import socket
from random import randint
import threading

class Server:
    """
    Usuários já cadastrados ficam armazenados no arquivo users.txt, no
    formato (tab-separated):

    USERNAME    PASSWORD
    """
    HOST = "127.0.0.1"
    USERSF = "users.txt"

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._logged_users = []
        # force creation of user file
        open(Server.USERSF,"r").close()

    def listen(self, port):
        self._bind_port(port)

        while True:
            self.socket.listen()
            conn, addr = self.socket.accept()
            client_thread = threading.Thread(target=self.read_commands, args=(conn, addr))
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
        while True:
            print("Received connection from", addr)
            data = conn.recv(1024)
            if not data:
                break

            print(f"Received: {data}")
            msg = data.decode("utf-8").split(";")
            print(f"Command: {msg[0]}")

            if msg[0] == "adduser":
                resp = self._adduser(msg[1:])
                print(resp)
                conn.sendmsg(bytes(f"{s};","utf-8") for s in resp)

            elif msg[0] == "passwd":
                resp = self._passwd(msg[1], msg[2], msg[3])
                print(resp)
                conn.sendmsg(bytes(s,"utf-8") for s in ";".join(resp))
            elif msg[0] == "login":
                resp = self._login(msg[1:])
                print(resp)
                conn.sendmsg(bytes(s,"utf-8") for s in ";".join(resp))
            elif msg[0] == "list":
                resp = self._list()
                print(resp)
                conn.sendmsg(bytes(s,"utf-8") for s in ";".join(resp))

    def disconnect(self):
        print("Closing socket")
        self.socket.close()

    def log_user(self, username):
        self._logged_users.append(username)

    def logout_user(self, username):
        self._logged_users.pop(username)

    def _list(self):
        return ["listACK"] + [u for u in self._logged_users]

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

    def _passwd(self, user, old_password, new_password):
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

