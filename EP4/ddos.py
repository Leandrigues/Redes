import time
import paho.mqtt.client as mqtt
from tqdm import tqdm
import subprocess
import sys

def bootstrap():
  keep_alive = 5000

  for i in range(100):
    print(f'Executando o client {i} with keep-alive', keep_alive)
    client = mqtt.Client(f'client{i}', protocol=mqtt.MQTTv5)
    client.connect('0.0.0.0', 1883, keep_alive)

  time.sleep(120)

bootstrap()