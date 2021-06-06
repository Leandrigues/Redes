import sys
from Server import Server

if __name__ == '__main__':
  port = sys.argv[1] if len(sys.argv) > 1 else 3000
  server = Server()
  server.listen(port)