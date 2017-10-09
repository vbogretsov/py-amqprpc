import asyncio

import aioamqp
import amqprpc


class Serv:

    def test(self, name):
        return "hello, {0}".format(name)


async def main():
    transport, protocol = await aioamqp.connect()
    codec = await amqprpc.server_codec(protocol, "serv")
    codec.register(Serv())
    # TODO(vbogretsov): handle close issue
    # await codec.close()
    # await protocol.close()
    # transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()