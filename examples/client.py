import asyncio

import aioamqp
import amqprpc


async def main():
    transport, protocol = await aioamqp.connect()
    channel = await protocol.channel()
    client = await amqprpc.register_client("serv", channel)
    res = await client.test("xxx")
    print(res)
    # await channel.close()
    # await protocol.close()
    # transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())