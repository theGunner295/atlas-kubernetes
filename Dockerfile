FROM steamcmd/steamcmd:ubuntu
LABEL maintainer="Redshift Enterprises"
LABEL version="0.1"
LABEL description="Redshift Atlas Shards"

ARG REDIS_PORT=6379
ARG SEAMLESS_PORT=27000
ARG GAME_PORT=5760
ARG QUERY_PORT=57560
ARG RCON_PORT=47560
ARG REDIS_SERVER_FQDN
ENV PUBLIC_IP="127.0.0.1"
ENV POD_TYPE="mgmt"
ENV SERVER_PASSWORD="Default123"
ENV X=0
ENV Y=0
ENV MAX_PLAYERS=20
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /cluster

COPY . .

RUN apt-get update \
&& apt-get install -y \
python3 python3-pip \
wine64 curl \
apt-transport-https ca-certificates curl
RUN curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | tee /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update

RUN export PYTHONPATH=/usr/bin/python \
&& pip install -r requirements.txt

EXPOSE ${REDIS_PORT}
EXPOSE ${SEAMLESS_PORT}
EXPOSE ${GAME_PORT}
EXPOSE ${QUERY_PORT}
EXPOSE ${RCON_PORT}

RUN [ ! -d "/cluster/atlas/ShooterGame" ] && mkdir -p /cluster/atlas/ShooterGame
RUN [ ! -d "/cluster/kubectl/" ] && mkdir -p /cluster/kubectl
ENTRYPOINT [ "+quit" ]
CMD [ "python3", "main.py" ]