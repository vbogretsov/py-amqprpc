import argparse
import asyncio
import random
import time

import aioamqp
import amqprpc


NUM_MSG = 10000

parser = argparse.ArgumentParser(description="Test RPC client.")
parser.add_argument(
    '--amqphost', dest='amqphost', action='store',
    default="localhost", help='AMQP broker host.')


async def run(amqphost):
    transport, protocol = await aioamqp.connect(host=amqphost)
    codec = await amqprpc.client_codec(protocol, "testrpc", amqprpc.Json)
    client = codec.client("Test")

    tasks = {}
    start = time.time()

    for i in range(NUM_MSG):
        args = (random.randint(0, 100), random.randint(0, 100))
        task = loop.create_task(client.Mul({"A": args[0], "B": args[1]}))
        tasks[args] = task

    for args, task in tasks.items():
        resp = await task
        assert resp == args[0] * args[1]

    print(NUM_MSG / (time.time() - start), "rps")

    await codec.close()
    await protocol.close()
    transport.close()


if __name__ == '__main__':
    args = parser.parse_args()
    random.seed(time.time())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args.amqphost))