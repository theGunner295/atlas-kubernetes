import json

def conabc(number):
    letter = chr(ord('@')+number)
    return letter

INPUT_FILE = 'C:\\Kubernetes\\ServerGrid4x4.json'
OUTPUT_FILE = 'C:\\Kubernetes\\New-ServerGrid4x4.json'


with open(INPUT_FILE,'r+') as ServerGrid_File:
    ServerGrid_Doc = ServerGrid_File
    ServerGrid = json.load(ServerGrid_Doc)


SeamlessPort = 27000
GamePort = 5760
QueryPort = 57560

iteration = 0
for servers in ServerGrid['servers']:
    ServerGrid['servers'][iteration]['name'] = (conabc(servers['gridX']+1) + str(servers['gridY']))
    ServerGrid['servers'][iteration]['port'] = QueryPort
    ServerGrid['servers'][iteration]['seamlessDataPort'] = SeamlessPort
    ServerGrid['servers'][iteration]['gamePort'] = GamePort
    ServerGrid['servers'][iteration]['ip'] = '77.68.50.4'
    iteration += 1
    SeamlessPort += 2
    GamePort += 2
    QueryPort += 2

with open(OUTPUT_FILE,'w') as NewServerGrid_File:
    json.dump(ServerGrid,NewServerGrid_File)