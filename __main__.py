import argparse
from clients import sr_client, gbn_client, sw_client
from servers import sr_server, gbn_server, sw_server


def parse_config(path, host_type):
    host_type_params = {'client':[('other_ip',str), ('other_port',int), ('ip',int), ('file_name',str), ('window',int)],
                        'server':[('port',int), ('window',int), ('random_seed',int), ('loss_prob',float)]}

    params = {}
    with open(path, 'r') as config_file:
        for key in host_type_params[host_type]:
            params[key[0]] = key[1](config_file.readline().replace('\n',''))
    return params


parser = argparse.ArgumentParser('a simple file transfer protocol implementation '
                                 'over 3 variants of reliable data tranfaer protocols:'
                                 ' stop and wait, selective repeat and go back N')

parser.add_argument('-i', '--interactive', action='store_true', help='weather this is an interactive client or not')
parser.add_argument('protocol', help='the transport layer protocol to use', choices=['gbn','sr', 'sw'])
parser.add_argument('host_type', choices=['client', 'server'], default='server', help='what type of host is this')
parser.add_argument('-f', '--file_name', help='name of the file the client wants to download')

cmd_config_group = parser.add_argument_group()
cmd_config_group.add_argument('-w', '--window', help='size of the window', type=int, default=15)

cmd_config_group.add_argument('--other_ip', help='ip of the other side, taken to be server\'s '
                                                 'ip in the client side')
cmd_config_group.add_argument('--other_port', help='port of the other side, taken to be server\'s'
                                                   ' port in the client side', type=int)
cmd_config_group.add_argument('--port', help='port of the calling side',type=int)
cmd_config_group.add_argument('--ip', help='ip of the calling side')

cmd_config_group.add_argument('--loss_prob', help='the packet loss probability to use in the simulation',
                              type=float, default=0)

cmd_config_group.add_argument('--random_seed', help='the packet loss probability to use in the simulation',
                              type=float, default=5)
config_grp = parser.add_mutually_exclusive_group()
config_grp.add_argument_group(cmd_config_group)
config_grp.add_argument('--config' ,help='path to the configuration file')
args = parser.parse_args()
actions = {'client':{'sr':sr_client.start_client,'gbn':gbn_client.start_client,'sw':sw_client.start_client},
           'server':{'sr':sr_server.start_server,'gbn':gbn_server.start_server,'sw':sw_server.start_server}}

params = parse_config(args.config, args.host_type) if args.config else vars(args)
print(params)
actions[args.host_type][args.protocol](**params)






