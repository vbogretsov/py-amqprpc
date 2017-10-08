import asyncio

import aioamqp
import amqprpc


class Serv:

    def test(self, name):
        return "hello, {0}".format(name)


async def main():
    transport, protocol = await aioamqp.connect()
    channel = await protocol.channel()
    # channel.basic_qos(prefetch_count=prefetch_count, connection_global=False)
    # await amqprpc.register_server(test, "test", channel)
    await amqprpc.register_server(Serv(), "serv", channel)

    # await channel.close()
    # await protocol.close()
    # transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()