#!/usr/bin/env bash
touch ./server_logs/sr_server.log
touch ./evaluation_out
touch ./
cd ..
server_pids=()
iters=0
port=20000
for protocol in sw sr gbn
do
    python3.6 ./HeroUDP ${protocol} server --port ${port} &
    server_pid=$!
    echo ${protocol}_serverpid is $server_pid
    server_pids+=($server_pid)
    for i in 1 2 3 4 5
    do
        iters=$((1+$iters))
        (python3.6 ./HeroUDP ${protocol} client --other_ip 127.0.0.1 --other_port ${port} -f $1 | tail -1) >> HeroUDP/evaluation_out &
        echo ${protocol}_client_${i}_pid is $!
    done
    port=$((1000+$port))

done

#cd HeroUDP

#x=$( cat ./evaluation_out | wc -l )
#echo $x
#echo iters $iters
#iters=$(($iters-1))
#while [ "$x" -le "$iters" ]
#do
 #   sleep 10
  #  x=$( cat ./evaluation_out | wc -l )
#done

#for pid in $server_pids
#do
   # kill -9 $server_pid
#done
