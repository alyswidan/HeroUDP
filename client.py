import asyncio


class EchoClientProtocol:
    def __init__(self, loop):
        self.loop = loop
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport


    def datagram_received(self, data, addr):
        print("Received:", data.decode())
        print("Close the socket")
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Socket closed, stop the event loop")
        loop = asyncio.get_event_loop()
        loop.stop()


async def get_msg():
    while True:
        msg = input()
        protocol.transport.sendto(msg.encode())


loop = asyncio.get_event_loop()
connect = loop.create_datagram_endpoint(lambda: EchoClientProtocol(loop), remote_addr=('127.0.0.1', 9999))

transport, protocol = loop.run_until_complete(connect)
loop.run_until_complete(loop.create_task(get_msg()))

loop.run_forever()

