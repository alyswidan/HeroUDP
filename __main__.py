import argparse
from clients import sr_client
from servers import sr_server

parser = argparse.ArgumentParser('a simple file transfer protocol implementation '
                                 'over 3 variants of reliable data tranfaer protocols:'
                                 ' stop and wait, selective repeat and go back N')
parser.add_argument('-i', '--interactive', action='store_true', help='weather this is an interactive client or not')
parser.add_argument('protocol', help='the transport layer protocol to use', choices=['gbn','sr', 'sw'])
parser.add_argument('host_type', choices=['client', 'server'], default='server', help='what type of host is this')
parser.add_argument('-f', '--filename', help='name of the file the client wants to download')
cmd_config_group = parser.add_argument_group()
cmd_config_group.add_argument('-w', '--window', help='size of the window', type=int, default=15)
cmd_config_group.add_argument('--max_seq_num', help='maximum sequence number to use, set to max(input, 2*window)',
                              type=int, default=-1)
cmd_config_group.add_argument('--other_ip', help='ip of the other side, taken to be server\'s '
                                                 'ip in the client side')
cmd_config_group.add_argument('--other_port', help='port of the other side, taken to be server\'s'
                                                   ' port in the client side', type=int)
cmd_config_group.add_argument('--port', help='port of the calling side',type=int)
cmd_config_group.add_argument('--ip', help='ip of the calling side')
cmd_config_group.add_argument('--loss_prob', help='the packet loss probability to use in the simulation',
                              type=float, default=0)
config_grp = parser.add_mutually_exclusive_group()
config_grp.add_argument_group(cmd_config_group)
config_grp.add_argument('--config', help='path to the configuration file')
args = parser.parse_args()

if args.host_type == 'client':
    sr_client.start_client(server_ip=args.other_ip, server_port=args.other_port,
                           file_name=args.filename,window_size=args.window,
                           max_seq_num=args.max_seq_num, loss_prob=args.loss_prob)

elif args.host_type == 'server':
    sr_server.startserver(welcoming_port=args.port, window_size=args.window,
                          loss_prob=args.loss_prob, max_seq_num=args.max_seq_num)


