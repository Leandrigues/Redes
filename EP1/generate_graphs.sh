#!/bin/bash

# psrecord $(pgrep my_mqtt_server) --duration 15 --plot without_clients.png
for i in {1..50}
do
  mosquitto_sub -V mqttv5 -t "topico" -p 1883 &
  sleep 0.1
done

for i in {1..50}
do
mosquitto_pub -V mqttv5 -t "topico" -m "mensagem" -p 1883
sleep 0.1
done

trap "killall background" EXIT
