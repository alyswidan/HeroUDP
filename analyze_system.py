from clients import sr_client, gbn_client, sw_client
from servers import sr_server, gbn_server, sw_server

actions = {'client':{'sr':sr_client.start_client,'gbn':gbn_client.start_client,'sw':sw_client.start_client},
           'server':{'sr':sr_server.start_server,'gbn':gbn_server.start_server,'sw':sw_server.start_server}}
