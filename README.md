# HeroUDP
An implementation of three reliable data transfer 
protocols: Stop and wait, go back N and selective 
repeat on top of UDP, with the ability to simulate packet loss and corruption for testing on the same machine.

### Usage
This project has a dependency on numpy to generate random choices for wether to corrupt packets and drop them.
This tool could be used to build new clients and servers that leverage these protocols by using the senders and receivers described below, the example servers and clients 
could also be used to try the system and perform the process described in the workflow section, the tool is invoked using the following 
`HeroUDP [client | server] [sr | gbn | sw] --config {name of config file}`
instead of using a config file options could be passed directly from the command line, invoke the tool using` HeroUDP --help` for more info about the available options.

### Repo Structure
The implementation of the protocols is split into
senders and receivers which are used by the clients 
and servers to send data to each other.
### Workflow
For each of the clients and servers the client starts 
by sending the file name it wants to download from the server,the server uses this
packet to know the port of the client.Upon receiving the packet, the server starts
a thread which in turn opens a socket to start communicating with the client, 
through this the socket the server sends the client a unique id for the client to label 
its files followed by the
number of packets it is going to send.The server then starts sending the file.
### UDT senders and receivers
The classes implementing the reliable protocols use udt_senders and udt_receivers
to send and receive packets instead of sending through the UDP socket directly.
#### UDT Senders
All udt senders have 2 main methods: send_ack and send_data, these are used by the
protocols to send data and acks respectively. Another variant is the LossyUDTSender
which uses the methods of udt sender to send the data, however it decides weather
the packet is to be dropped or not before sending it.As for the corruption of packets
we use the CorruptingUDTSender which flips some of the bits of the packet before sending 
it, it does this also with some probability set as a parameter to the class.
#### UDT Receivers
Udt receivers only have two variants a basic one that receives the raw bytes from the
socket and wraps them into a packet object, the method also validate the integrity
of the packet using the checksum appended to the packet- we use the `Fletcher-16` 
algorithm to calculate check sums, if the packet doesnt pass the check the method
returns `None` to the caller.The other variant is an Interruptable udt receiver
that uses the non blocking python sockets and could be interrupted while waiting for
a packet to arrive.
### The reliable protocols
#### Overview
Both GBN and Selective repeat are implemented in a similar manner as opposed to
Stop and Wait which we used a different approach in its implementation, these
approaches are discussed in the following sections.
#### Stop-and-wait
##### The sender
The sender uses two classes two nested classes to represent the two types
of states namely waiting for ack and waiting for data, the implementation then
directly implements the state machine for the protocol.
#####The receiver
This one uses the same approach as with the sender, it also uses a nested class
to represent the waiting for ack state and uses this to implement the state machine.
#### Go-Back-N
##### The sender
In this implementation the server runs on a thread and the sender runs on another 
thread, the sender runs continuously in a loop waiting for one of two events to happen,
these two events are either that of the server places a data chunk on a shared queue,
or another thread running in parallel that receives acks and places them on another 
shared queue. As for the data chunk the server places the chunk into the window, starts
a timer if this is the base and sends it through the udt sender. As for the acks the 
main loop picks an ack from the queue and updates the window accordingly.
##### The receiver 
The receiver is very similar to the sender in that it has a main loop waiting 
for data to arrive from the network, the data received is delivered to the client
if it is the expected packet otherwise it is dropped.
#### Selective-Repeat
##### The sender
As for the sender, the same idea of the main loop waiting for data from the server
and the thread waiting for acks is still there, the main difference is in the 
presence of a timer for each packet as well as in the way the window is adjusted 
when a packet arrives.Also we use circular sequence number where the maximum sequence
number is set to double the window if the user left it out.
##### The receiver
The receiver is also similar to the GBN receiver with the difference being the 
existence of a window where packets are buffered and delivered to the client in order.

