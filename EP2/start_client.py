import sys
from Client import Client

HOST = '127.0.0.1'

if __name__ == '__main__':
  port = sys.argv[1] if len(sys.argv) > 1 else 3000
  server_ip = sys.argv[2] if len(sys.argv) > 2 else HOST
  
  client = Client()
  client.connect(port, HOST)