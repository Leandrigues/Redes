import socket
from random import randint

class Server:
    """
    Usuários já cadastrados ficam armazenados no arquivo users.txt, no
    formato (tab-separated): 

    USERNAME    PASSWORD
    """
    # Sim, é horrível, mas n sei fazer cadastro ainda e quero começar nas
    # outras coisas.
    
    HOST = '127.0.0.1'
    USERSF = 'users.txt'

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._logged_users = []
        # force creation of user file
        open(Server.USERSF,"r").close()

    def connect(self, port):
        try:
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)
        except OSError:
            # Por enquanto, só pra evitar o bug da porta ficar ocupada
            # depois de finalizar o processo, tô adicionando um random
            # pra pegar uma porta desocupada
            port += randint(1, 99)
            self.socket.bind((Server.HOST, port))
            print("Listening in port", port)

        self.socket.listen()

        conn, addr = self.socket.accept()
        while True:
            print("Received connection from", addr)
            # ct = client_thread(conn) # Pra no futuro usar threads
            # ct.run()
            data = conn.recv(1024)
            if not data:
                break
            # conn.sendall(data)
            print(f"Received: {data}")
            msg = data.decode("utf-8").split(";")
            print(f"Command: {msg[0]}")

            if msg[0] == "adduser":
                resp = self._adduser(msg[1:])
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

        self.disconnect()

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
                        return ["loginACK"]
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
            users = handle.read().split("\n")
            
            i = 0
            for u in users:
                if u == '':
                    break
                username = u.split("\t")[0]
                if username > new_username:
                    break
                if username == new_username:
                    return ["adduserERR", "USEREXISTS"]

                i = i+1

            # Update userlist
            users = users[:i] + ['\t'.join(args)] + users[i+1:]

        # Sobrescreve arquivo
        with open(Server.USERSF,'w+') as handle:
            handle.write('\n'.join(users))
        
        return ["adduserACK"]