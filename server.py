import asyncio


class EchoServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print('Received %r from %s' % (message, addr))

        self.transport.sendto(data, addr)


loop = asyncio.get_event_loop()
print("Starting UDP server")


listen = loop.create_datagram_endpoint(EchoServerProtocol, local_addr=('127.0.0.1', 9999))

transport, protocol = loop.run_until_complete(listen)
loop.run_forever()



