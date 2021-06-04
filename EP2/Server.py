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
        # force creation of user file
        open(Server.USERSF,"w+").close()

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
            conn.sendall(data)
            print(f"Received: {data}")
            msg = data.decode("utf-8").split(";")
            print(f"Command: {msg[0]}")

            if msg[0] == "adduser":
                resp = self._adduser(msg[1:])

                print(resp)
                conn.sendmsg(bytes(s,"utf-8") for s in resp)

        self.disconnect()

    def disconnect(self):
        print("Closing socket")
        self.socket.close()

    def _adduser(self, args):
        if len(args) != 2:
            print("adduser requires 2 arguments")
            return ["adduserACK","ARGNUM"]

        new_username = args[0]
        with open(Server.USERSF,"r") as handle:
            # Lê todos os usuários para a memória pq fazer a inserção no
            # arquivo em si é muito trampo
            users = handle.read().split("\n")
            user_it = iter(users)
            
            i = 0
            for cur_user in user_it:
                if cur_user == '':
                    break
                username = cur_user.split("\t")[0]
                if username > new_username:
                    break
                if username == new_username:
                    # TODO: retornar alguma indicação pro cliente
                    print("Usuário já cadastrado.\n")
                    return ["adduserACK","USEREXISTS"]

                i = i+1

            # Update userlist
            users = users[:i] + ['\t'.join(args)] + users[i+1:]

        # Sobrescreve arquivo
        with open(Server.USERSF,'w+') as handle:
            handle.write('\n'.join(users))
        
        return ["adduserACK","OK"]