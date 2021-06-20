run:
	echo "Generating keys" && \
	openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem -subj "/C=BR/ST=Sao Paulo/L=Sao Paulo/CN=jogo-da-velha-server/" && \
	echo "Starting server" && \
	python3 start_server.py $(port) & \
	sleep 3 && \
	echo "Starting client" && \
	python3 start_client.py $(port)
