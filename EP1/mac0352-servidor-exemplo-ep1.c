/* Por Prof. Daniel Batista <batista@ime.usp.br>
 * Em 4/4/2021
 * 
 * Um código simples de um servidor de eco a ser usado como base para
 * o EP1. Ele recebe uma linha de um cliente e devolve a mesma linha.
 * Teste ele assim depois de compilar:
 * 
 * ./ep1-servidor-exemplo 8000
 * 
 * Com este comando o servidor ficará escutando por conexões na porta
 * 8000 TCP (Se você quiser fazer o servidor escutar em uma porta
 * menor que 1024 você precisará ser root ou ter as permissões
 * necessáfias para rodar o código com 'sudo').
 *
 * Depois conecte no servidor via telnet. Rode em outro terminal:
 * 
 * telnet 127.0.0.1 8000
 * 
 * Escreva sequências de caracteres seguidas de ENTER. Você verá que o
 * telnet exibe a mesma linha em seguida. Esta repetição da linha é
 * enviada pelo servidor. O servidor também exibe no terminal onde ele
 * estiver rodando as linhas enviadas pelos clientes.
 * 
 * Obs.: Você pode conectar no servidor remotamente também. Basta
 * saber o endereço IP remoto da máquina onde o servidor está rodando
 * e não pode haver nenhum firewall no meio do caminho bloqueando
 * conexões na porta escolhida.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <netdb.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

#define LISTENQ 1
#define MAXDATASIZE 100
#define MAXLINE 4096

char* getTopic(char *input, int length, int offset) {
    int i = offset;
    int j = 0;
    int end = offset + length;
    char *topicName = malloc(sizeof(char) * length);
    while (i != end) {
        topicName[j++] = input[i++];
    }
    return topicName;
}

FILE* writeInTopic(char *topic, char *message) {
    FILE* f = fopen(topic, "a");
    if (f == NULL) {
        printf("Error creating from topic '%s'\n", topic);
        exit(1);
    }
    printf("Sending '%s' to '%s'\n", message, topic);
    fprintf(f, "%s\n", message);
    fclose(f);
    return f;
}

char* buildResponse(char * message, int messageLength, char* topic, int topicLength, int connfd) {
    int totalLength = messageLength + topicLength + 5;
    char response[totalLength];
    response[0] = 0x30;
    response[1] = topicLength + messageLength + 3;
    response[2] = 0x00;
    response[3] = topicLength;
    int i;
    int j;
    // Write topic in response
    for (i = 4; i < 4 + topicLength; i++) {
        response[i] = topic[i-4];
        printf("%x ", response[i-4]);
    }
    response[i] = 0x00;

    for(j = i+1; j < i + 1 + messageLength; j++) {
        response[j] = message[j-i-1];
        printf("%x ", response[j]);

    }
    printf("DEBUG: %d\n", totalLength);
    write(connfd,  response, totalLength);

}

void readTopic(char *topic, int topicLength, int connfd) {
    FILE* f = fopen(topic, "r");
    fseek(f, 0, SEEK_END);
    int oldSize = ftell(f); 
    int newSize;
    int read;
    int diff;
    char* line;
    size_t len = 0;

    if (f == NULL) {
        printf("Error reading from topic '%s'\n", topic);
        exit(1);
    }

    while(1==1) {
        fseek(f, 0, SEEK_END);
        newSize = ftell(f);
        if (newSize != oldSize) {
            diff = newSize - oldSize;
            oldSize = newSize;
            fseek(f, -1 * diff, SEEK_END);
            read = getline(&line, &len, f);
            printf("Added line: %s\n", line);
            buildResponse(line, diff, topic, topicLength, connfd);
            // char response[9] = {0x30, 0x07, 0x00, 0x01, 0x61, 0x00, 0x61, 0x2f, 0x62};
            // write(connfd,  response, 9);
        }
    }
}

char* getMessage(char *input, int offset, int length) {
    int i = offset;
    int j = 0;
    char *message = malloc(sizeof(char) * length);

    while (i != offset + length) {
        message[j++] = input[i++];
    }
    return message;
}

void handleConnect(char *recvline, int connfd) {
    printf("Received connection request\n");
    char connAck[5] = {0x20, 0x03, 0x00, 0x00, 0x00};
    write(connfd, connAck, 5);
}

void handlePublish(char *recvline) {
    uint16_t topicLength = recvline[3];
    int remainingLength = (int) recvline[1];
    int messageLength = remainingLength - topicLength - 3;
    char *topic = getTopic(recvline, topicLength, 4);
    char *message = getMessage(recvline, topicLength + 5, messageLength);
    FILE *f = writeInTopic(topic, message);

    // printf("MESSAGE: %s\n", message);
    // printf("MESSAGE LENGTH: %d\n", messageLength);
    // printf("TOPIC: %s\n", topic);
    // printf("Received publish request: %x\n", recvline[0]);
    // printf("TOPIC LENGTH: %d\n", topicLength);
    // printf("REMAINING LENGTH: %d\n", remainingLength);
}

void handleSubscribe(char *recvline, int connfd) {
    // printf("recvline[4]: %x\n", recvline[3]);
    char subAck[7] = {0x90, 0x05, recvline[3], 0x03, 0x00, 0x00, 0x00};
    write(connfd,  subAck, 7);
    uint16_t topicLength = recvline[6];
    char* topic = getTopic(recvline, topicLength, 7);
    printf("Received subscribe request to topic: %s\n", topic);
    // char response[9] = {0x30, 7, 0x00, 0x01, 0x61, 0x00, 0x61, 0x2f, 0x62};
    // write(connfd,  response, 9);
    readTopic(topic, topicLength, connfd);
}

int main (int argc, char **argv) {
    /* Os sockets. Um que será o socket que vai escutar pelas conexões
     * e o outro que vai ser o socket específico de cada conexão */
    int listenfd, connfd;
    /* Informações sobre o socket (endereço e porta) ficam nesta struct */
    struct sockaddr_in servaddr;
    /* Retorno da função fork para saber quem é o processo filho e
     * quem é o processo pai */
    pid_t childpid;
    /* Armazena linhas recebidas do cliente */
    char recvline[MAXLINE + 1];
    /* Armazena o tamanho da string lida do cliente */
    ssize_t n;

    if (argc != 2) {
        fprintf(stderr,"Uso: %s <Porta>\n",argv[0]);
        fprintf(stderr,"Vai rodar um servidor de echo na porta <Porta> TCP\n");
        exit(1);
    }

    /* Criação de um socket. É como se fosse um descritor de arquivo.
     * É possível fazer operações como read, write e close. Neste caso o
     * socket criado é um socket IPv4 (por causa do AF_INET), que vai
     * usar TCP (por causa do SOCK_STREAM), já que o MQTT funciona sobre
     * TCP, e será usado para uma aplicação convencional sobre a Internet
     * (por causa do número 0) */
    if ((listenfd = socket(AF_INET, SOCK_STREAM, 0)) == -1) {
        perror("socket :(\n");
        exit(2);
    }

    /* Agora é necessário informar os endereços associados a este
     * socket. É necessário informar o endereço / interface e a porta,
     * pois mais adiante o socket ficará esperando conexões nesta porta
     * e neste(s) endereços. Para isso é necessário preencher a struct
     * servaddr. É necessário colocar lá o tipo de socket (No nosso
     * caso AF_INET porque é IPv4), em qual endereço / interface serão
     * esperadas conexões (Neste caso em qualquer uma -- INADDR_ANY) e
     * qual a porta. Neste caso será a porta que foi passada como
     * argumento no shell (atoi(argv[1]))
     */
    bzero(&servaddr, sizeof(servaddr));
    servaddr.sin_family      = AF_INET;
    servaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    servaddr.sin_port        = htons(atoi(argv[1]));
    if (bind(listenfd, (struct sockaddr *)&servaddr, sizeof(servaddr)) == -1) {
        perror("bind :(\n");
        exit(3);
    }

    /* Como este código é o código de um servidor, o socket será um
     * socket passivo. Para isto é necessário chamar a função listen
     * que define que este é um socket de servidor que ficará esperando
     * por conexões nos endereços definidos na função bind. */
    if (listen(listenfd, LISTENQ) == -1) {
        perror("listen :(\n");
        exit(4);
    }

    // printf("[Servidor no ar. Aguardando conexões na porta %s]\n",argv[1]);
    // printf("[Para finalizar, pressione CTRL+c ou rode um kill ou killall]\n");

    /* O servidor no final das contas é um loop infinito de espera por
     * conexões e processamento de cada uma individualmente */
	for (;;) {
        /* O socket inicial que foi criado é o socket que vai aguardar
         * pela conexão na porta especificada. Mas pode ser que existam
         * diversos clientes conectando no servidor. Por isso deve-se
         * utilizar a função accept. Esta função vai retirar uma conexão
         * da fila de conexões que foram aceitas no socket listenfd e
         * vai criar um socket específico para esta conexão. O descritor
         * deste novo socket é o retorno da função accept. */
        if ((connfd = accept(listenfd, (struct sockaddr *) NULL, NULL)) == -1 ) {
            perror("accept :(\n");
            exit(5);
        }

        /* Agora o servidor precisa tratar este cliente de forma
         * separada. Para isto é criado um processo filho usando a
         * função fork. O processo vai ser uma cópia deste. Depois da
         * função fork, os dois processos (pai e filho) estarão no mesmo
         * ponto do código, mas cada um terá um PID diferente. Assim é
         * possível diferenciar o que cada processo terá que fazer. O
         * filho tem que processar a requisição do cliente. O pai tem
         * que voltar no loop para continuar aceitando novas conexões.
         * Se o retorno da função fork for zero, é porque está no
         * processo filho. */
        if ( (childpid = fork()) == 0) {
            /**** PROCESSO FILHO ****/
            // printf("[Uma conexão aberta]\n");
            /* Já que está no processo filho, não precisa mais do socket
             * listenfd. Só o processo pai precisa deste socket. */
            close(listenfd);

            /* Agora pode ler do socket e escrever no socket. Isto tem
             * que ser feito em sincronia com o cliente. Não faz sentido
             * ler sem ter o que ler. Ou seja, neste caso está sendo
             * considerado que o cliente vai enviar algo para o servidor.
             * O servidor vai processar o que tiver sido enviado e vai
             * enviar uma resposta para o cliente (Que precisará estar
             * esperando por esta resposta) 
             */

            /* ========================================================= */
            /* ========================================================= */
            /*                         EP1 INÍCIO                        */
            /* ========================================================= */
            /* ========================================================= */
            /* TODO: É esta parte do código que terá que ser modificada
             * para que este servidor consiga interpretar comandos MQTT  */
            uint8_t identifier;

            n=read(connfd, recvline, MAXLINE);
            identifier = recvline[0];

            if ((fputs(recvline,stdout)) == EOF) {
                perror("fputs :( \n");
                exit(6);
            }
            // CONNECT request
            if (identifier == 16) {
                handleConnect(recvline, connfd);
            }

            n=read(connfd, recvline, MAXLINE);
            identifier = recvline[0];
            // printf("IDENTIFIER: %d\n", identifier);
            // PUBLISH request
            if (identifier == 48) {
                handlePublish(recvline);
            }

            // SUBSCRIBE request
            if (identifier == 130) {
                handleSubscribe(recvline, connfd);
            }


            /* ========================================================= */
            /* ========================================================= */
            /*                         EP1 FIM                           */
            /* ========================================================= */
            /* ========================================================= */

            /* Após ter feito toda a troca de informação com o cliente,
             * pode finalizar o processo filho */
            // printf("[Uma conexão fechada]\n");
            exit(0);
        }
        else
            /**** PROCESSO PAI ****/
            /* Se for o pai, a única coisa a ser feita é fechar o socket
             * connfd (ele é o socket do cliente específico que será tratado
             * pelo processo filho) */
            close(connfd);
    }
    exit(0);
}
