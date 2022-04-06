FROM steamcmd/steamcmd:ubuntu-18
LABEL maintainer="Redshift Enterprises"
LABEL version="0.1"
LABEL description="Redshift Atlas Shards"

ARG REDIS_PORT
ARG SEAMLESS_PORT
ARG GAME_PORT
ARG QUERY_PORT
ARG RCON_PORT
ARG REDIS_SERVER_FQDN
ENV PUBLIC_IP="127.0.0.1"
ENV POD_TYPE="mgmt"
ENV SERVER_PASSWORD="Default123"
ENV X=0
ENV Y=0
ENV MAX_PLAYERS=20

WORKDIR /cluster

COPY . .

RUN apt-get update
#RUN apt-get install -y <aptrequirements.txt
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN apt-get install -y wine64
RUN apt-get install -y curl
#RUN apt-get install -y lib32gcc-s1 steamcmd
RUN apt-get install -y apt-transport-https ca-certificates curl
RUN curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | tee /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update

RUN pip install -r requirements.txt

EXPOSE ${REDIS_PORT}}
EXPOSE ${SEAMLESS_PORT}
EXPOSE ${GAME_PORT}
EXPOSE ${QUERY_PORT}
EXPOSE ${RCON_PORT}

RUN [ ! -d "/cluster/atlas/ShooterGame" ] && mkdir -p /cluster/atlas/ShooterGame
RUN [ ! -d "/cluster/kubectl/" ] && mkdir -p /cluster/kubectl
CMD [ "python3", "main.py" ]