import os
from os.path import exists
from time import sleep
import socket
import sys
import yaml
import regex
from .lib.functions import alphabet_position,extract_num,permissive_json_loads

## Environment variables
""" 
ARG REDIS_PORT
ARG SEAMLESS_PORT
ARG GAME_PORT
ARG QUERY_PORT
ARG RCON_PORT
ENV PUBLIC_IP="127.0.0.1"
ENV POD_TYPE="mgmt"
ENV SERVER_PASSWORD="Default123"
ENV X=0
ENV Y=0
ENV MAX_PLAYERS=20
 """


gw = os.popen("ip -4 route show default").read().split()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((gw[2], 0))
IP_addr = s.getsockname()[0]


if (os.environ.get('POD_TYPE') == 'mgmt'):
    tries = 0
    for (not exists('/cluster/kubectl/config')):
        tries += 1
        print('Kubectl config missing from /cluster/kubectl')
        sleep(60)
        if tries > 10:
            os._exit(1)
    tries = 0
    for (not (exists('/cluster/atlas/ShooterGame/ServerGrid.ServerOnly.json') and exists('/cluster/atlas/ShooterGame/ServerGrid.json'))):
        tries += 1
        print('Atlas server config missing from /cluster/atlas/ShooterGame/')
        print('Config files required are ServerGrid.ServerOnly.json and ServerGrid.json')
        sleep(60)
        if tries > 10:
            os._exit(1)

    os.system('apt-get install -y kubectl')
    if (not os.environ.get('REDIS_SERVER_FQDN')):
        print('Creating redis service')
        with open("/cluster/kubectl/config", "rt") as kubeconf_file:
            kubeconf = yaml.safe_load(kubeconf_file)
        KubeURL = kubeconf['clusters'][0]['cluster']['server']
        ClusterExtIP = regex.findall(r'(?:\d{1,3}\.)+(?:\d{1,3})',KubeURL)[0]
        REDIS_LOCATION = 'atlas-redis.redis.svc.cluster.local'
    import json
    REDIS_LOCATION = os.environ.get('REDIS_SERVER_FQDN')
    with open('/cluster/atlas/ShooterGame/ServerGrid.ServerOnly.json','r+') as ServerGrid_ServerOnly_File:
        ServerGrid_ServerOnly = json.load(ServerGrid_ServerOnly_File)
        print('Setting Redis URL in server config files')
        print('Redis FQDN is ' + REDIS_LOCATION)
        for conf in ServerGrid_ServerOnly['DatabaseConnections']:
            conf['URL']=REDIS_LOCATION
        ServerGrid_ServerOnly_Dump = json.dumps(ServerGrid_ServerOnly)
        ServerGrid_ServerOnly_File.write(ServerGrid_ServerOnly_Dump)

    with open('/cluster/atlas/ShooterGame/ServerGrid.json','r+') as ServerGrid_File:
        ServerGrid_Doc = ServerGrid_File
        ServerGrid = json.load(ServerGrid_Doc)

    instances = {}
    iteration = 0
    SeamlessPort = 27000
    GamePort = 5760
    QueryPort = 57560
    RCONPort = 47560
    for servers in ServerGrid['servers']:
        servername = servers['name']
        instances.insert(iteration,{
            'x': (int(alphabet_position(servername.split(extract_num(servername))[0]))-1),
            'y': (int(extract_num(servername))-1),
            'SeamlessPort': SeamlessPort,
            'GamePort': GamePort,
            'QueryPort': QueryPort,
            'RCONPort': RCONPort
        })
        iteration += 1
        SeamlessPort += 2
        GamePort += 2
        QueryPort += 2
        RCONPort += 2

    print('Creating required namespaces')
    os.system('kubectl apply -f /cluster/yaml/namespace.yaml')
    # Importing yaml service templates in preperation for full deployment
    ServiceTemplate_Path = "/cluster/yamltemplates/service.yaml"
    with open(ServiceTemplate_Path) as st:
        ServiceTemplate = yaml.load(st,Loader=yaml.FullLoader)
    DeploymentTemplate_Path = "/cluster/yamltemplates/deployment.yaml"
    with open(DeploymentTemplate_Path) as st:
        DeploymentTemplate = yaml.load(st,Loader=yaml.FullLoader)
    RedisClear = ('externalIPs')
    RedisService = ServiceTemplate
    RedisService['spec'].pop(RedisClear)
    #RedisService['spec']['externalIPs']=['127.10.0.1']
    RedisService['spec']['ports'] = [{'name': 'tcp6379', 'port': 6379, 'protocol': 'TCP', 'targetPort': 6379}]
    RedisService['metadata']['name'] = 'atlas-redis'
    RedisService['metadata']['namespace']='atlas-shards'
    RedisService['metadata']['labels'] = {'app':'Atlas-Redis'}
    RedisService['spec']['selector'] = {'app': 'atlas-redis'}
    RedisService_Path = "/cluster/yaml/RedisService.yaml"
    with open(RedisService_Path,"w") as RedisService_File:
        yaml.dump(RedisService, RedisService_File)
    os.system('kubectl apply -f /cluster/yaml/RedisService.yaml')
    with open(ServiceTemplate_Path) as st:
        ServiceTemplate = yaml.load(st,Loader=yaml.FullLoader)

    RedisDeployment=DeploymentTemplate
    RedisDeployment['metadata']['name'] = 'redis-deployment'
    RedisDeployment['metadata']['namespace'] = 'atlas-shards'
    RedisDeployment['spec']['selector']['matchLabels'] = {'app':'redis'}
    RedisDeployment['spec']['template']['metadata']['labels']['app'] = 'Atlas-Redis'
    RedisDeployment['spec']['template']['spec']['containers'][0]['name'] = 'atlas-redis'
    RedisDeployment['spec']['template']['spec']['containers'][0]['ports'][0]['name'] = 'tcp6379'
    RedisDeployment['spec']['template']['spec']['containers'][0]['ports'][0]['containerPort'] = 6379
    RedisDeployment['spec']['template']['spec']['containers'][0]['ports'][0]['protocol'] = 'TCP'
    RedisDeployment['spec']['template']['spec']['containers'][0]['env'] = [
        {'name': 'POD_TYPE', 'value': 'redis'},
        {'name': 'REDIS_PORT', 'value': 6379}]
    
    RedisDeployment_Path = "/cluster/yaml/RedisDeployment.yaml"
    with open(RedisDeployment_Path,"w") as RedisDeployment_File:
        yaml.dump(RedisDeployment, RedisDeployment_File)
    os.system('kubectl apply -f /cluster/yaml/RedisDeployment.yaml')

    with open(DeploymentTemplate_Path) as st:
        DeploymentTemplate = yaml.load(st,Loader=yaml.FullLoader)

    AtlasService = ServiceTemplate
    AtlasService['spec']['externalIPs']=[ClusterExtIP]
    AtlasClear = ('ports')
    AtlasService['spec'].pop(AtlasClear)
    AtlasService['spec']['ports'] = []
    iteration = 0
    for servers in instances:
        SeamlessPortNameTCP = "tcp" + str(servers['SeamlessPort'])
        GamePortNameTCP = "tcp" + str(servers['GamePort'])
        QueryPortNameTCP = "tcp" + str(servers['QueryPort'])
        RCONPortNameTCP = "tcp" + str(servers['RCONPort'])
        SeamlessPortNameUDP = "udp" + str(servers['SeamlessPort'])
        GamePortNameUDP = "udp" + str(servers['GamePort'])
        QueryPortNameUDP = "udp" + str(servers['QueryPort'])
        RCONPortNameUDP = "udp" + str(servers['RCONPort'])
        AtlasService['spec']['ports'].insert(0,{'name': SeamlessPortNameTCP, 'port': servers['SeamlessPort'], 'protocol': 'TCP', 'targetPort': servers['SeamlessPort']})
        AtlasService['spec']['ports'].insert(0,{'name': SeamlessPortNameUDP, 'port': servers['SeamlessPort'], 'protocol': 'UDP', 'targetPort': servers['SeamlessPort']})
        AtlasService['spec']['ports'].insert(0,{'name': GamePortNameTCP, 'port': servers['GamePort'], 'protocol': 'TCP', 'targetPort': servers['GamePort']})
        AtlasService['spec']['ports'].insert(0,{'name': GamePortNameUDP, 'port': servers['GamePort'], 'protocol': 'UDP', 'targetPort': servers['GamePort']})
        AtlasService['spec']['ports'].insert(0,{'name': QueryPortNameTCP, 'port': servers['QueryPort'], 'protocol': 'TCP', 'targetPort': servers['QueryPort']})
        AtlasService['spec']['ports'].insert(0,{'name': QueryPortNameUDP, 'port': servers['QueryPort'], 'protocol': 'UDP', 'targetPort': servers['QueryPort']})
        AtlasService['spec']['ports'].insert(0,{'name': RCONPortNameTCP, 'port': servers['RCONPort'], 'protocol': 'TCP', 'targetPort': servers['RCONPort']})
        AtlasService['spec']['ports'].insert(0,{'name': RCONPortNameUDP, 'port': servers['RCONPort'], 'protocol': 'UDP', 'targetPort': servers['RCONPort']})
        iteration += 1
    AtlasService['metadata']['name'] = 'atlas'
    AtlasService['metadata']['namespace']='atlas-shards'
    AtlasService['metadata']['labels'] = {'app':'Atlas'}
    AtlasService['spec']['selector'] = {'app': 'atlas'}
    AtlasService_Path = "/cluster/yaml/AtlasService.yaml"
    with open(AtlasService_Path,"w") as AtlasService_File:
        yaml.dump(AtlasService, AtlasService_File)
    os.system('kubectl apply -f /cluster/yaml/AtlasService.yaml')

    AtlasDeployment_Path = "/cluster/yaml/AtlasDeployment.yaml"
    AtlasDeployment=DeploymentTemplate
    AtlasDeployment['metadata']['name'] = 'atlas-deployment'
    AtlasDeployment['metadata']['namespace'] = 'atlas-shards'
    AtlasDeployment['spec']['selector']['matchLabels'] = {'app':'Atlas'}
    AtlasDeployment['spec']['template']['metadata']['labels']['app'] = 'Atlas'
    iteration = 0
    for servers in instances:
        ContainerName = "atlas-" + str(servers['x']) + "-" + str(servers['y'])
        SeamlessPortNameTCP = "tcp" + str(servers['SeamlessPort'])
        GamePortNameTCP = "tcp" + str(servers['GamePort'])
        QueryPortNameTCP = "tcp" + str(servers['QueryPort'])
        RCONPortNameTCP = "tcp" + str(servers['RCONPort'])
        SeamlessPortNameUDP = "udp" + str(servers['SeamlessPort'])
        GamePortNameUDP = "udp" + str(servers['GamePort'])
        QueryPortNameUDP = "udp" + str(servers['QueryPort'])
        RCONPortNameUDP = "udp" + str(servers['RCONPort'])
        AtlasDeployment['spec']['template']['spec']['containers'].insert(len(AtlasDeployment['spec']['template']['spec']['containers']),{})
        AtlasDeployment['spec']['template']['spec']['containers'][iteration]['image'] = 'awesomejack295/atlas-kubernetes'
        AtlasDeployment['spec']['template']['spec']['containers'][iteration]['name'] = ContainerName
        AtlasDeployment['spec']['template']['spec']['containers'][iteration]['ports'] = [
            {'name' : SeamlessPortNameTCP, 'containerPort' : servers['SeamlessPort'], 'protocol' : 'TCP'},
            {'name' : SeamlessPortNameUDP,'containerPort' : servers['SeamlessPort'], 'protocol' : 'UDP'},
            {'name' : GamePortNameTCP, 'containerPort' : servers['GamePort'], 'protocol' : 'TCP'},
            {'name' : GamePortNameUDP,'containerPort' : servers['GamePort'], 'protocol' : 'UDP'},
            {'name' : QueryPortNameTCP, 'containerPort' : servers['QueryPort'], 'protocol' : 'TCP'},
            {'name' : QueryPortNameUDP,'containerPort' : servers['QueryPort'], 'protocol' : 'UDP'},
            {'name' : RCONPortNameTCP, 'containerPort' : servers['RCONPort'], 'protocol' : 'TCP'},
            {'name' : RCONPortNameUDP,'containerPort' : servers['RCONPort'], 'protocol' : 'UDP'}]
        AtlasDeployment['spec']['template']['spec']['containers'][iteration]['env'] = [
            {'name': 'X', 'value': str(servers['x'])},
            {'name': 'Y', 'value': str(servers['y'])},
            {'name': 'SEAMLESS_PORT', 'value': SeamlessPort},
            {'name': 'GAME_PORT', 'value': GamePort},
            {'name': 'QUERY_PORT', 'value': QueryPort},
            {'name': 'RCON_PORT', 'value': RCONPort}]
        iteration += 1
    AtlasDeployment['spec']['template']['spec']['containers'].pop()
    
    with open(AtlasDeployment_Path,"w") as AtlasDeployment_File:
        yaml.dump(AtlasDeployment, AtlasDeployment_File)
        
    os.system('kubectl apply -f /cluster/yaml/AtlasDeployment.yaml')

    os.system('steamcmd +force_install_dir /cluster/atlas +login anonymous +app_update 1006030 +quit')

if (os.environ.get('POD_TYPE') == 'redis'):
    print('Running redis db on ' +  IP_addr)
    print('Note that this is NOT the cluster ip')

    os.system('/usr/bin/wine /cluster/atlas/AtlasTools/RedisDatabase/redis-server.exe /cluster/atlas/AtlasTools/RedisDatabase/redis.conf')



if (os.environ.get('POD_TYPE') == 'worker'):
    ServerName = os.environ.get('X') + "-" + os.environ.get('Y')
    XCoords = os.environ.get('X')
    YCoords = os.environ.get('Y')
    SEAMLESS_PORT = os.environ.get('SEAMLESS_PORT')
    GAME_PORT = os.environ.get('GAME_PORT')
    QUERY_PORT = os.environ.get('QUERY_PORT')
    RCON_PORT = os.environ.get('RCON_PORT')
    SERVER_PASSWORD = os.environ.get('SERVER_PASSWORD')
    MAX_PLAYERS =  os.environ.get('MAX_PLAYERS')
    PUBLIC_IP = os.environ.get('PUBLIC_IP')

    ServerLaunchCommand = "/cluster/atlas/ShooterGame/Binaries/Win64/ShooterGameServer.exe  Ocean?ServerX=" + XCoords + "?ServerY=" + YCoords + "?AltSaveDirectoryName=10?ServerAdminPassword=" + SERVER_PASSWORD + "?MaxPlayers=" + MAX_PLAYERS + "ReservedPlayerSlots=10?QueryPort=" + QUERY_PORT + "?Port=" + GAME_PORT + "?RCONEnabled=true?RCONPort=" + RCON_PORT + "?SeamlessIP=" + PUBLIC_IP + " -log -server"
    WineLauncher = "/usr/bin/wine " + ServerLaunchCommand
    os.system(WineLauncher)