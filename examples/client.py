import asyncio
# import datetime
import time

import aioamqp
import amqprpc


NUM_MSG = 1000


async def main():
    transport, protocol = await aioamqp.connect()
    codec = await amqprpc.client_codec(protocol, "serv")
    client = codec.client("Serv")

    tasks = []
    start = time.time()
    for i in range(NUM_MSG):
        tasks.append(loop.create_task(client.test("a")))
    for task in tasks:
        await task
    print("calls:", (NUM_MSG / (time.time() - start)), "qps")
    # TODO(vbogretsov): handle close issue
    # await codec.close()
    # await protocol.close()
    # transport.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())