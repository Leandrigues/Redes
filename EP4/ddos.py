from subprocess import Popen
import time

def bootstrap():
  procs = []
  for i in range(100):
    p = Popen('mosquitto_sub -V mqttv5 -t "topic" -k 10000', shell=True)
    procs.append(p)
    print(f"{i}: {p}")

  time.sleep(40)
  for p in procs:
    p.kill()

bootstrap()