import argparse
import asyncio
import signal

import aioamqp
import amqprpc


parser = argparse.ArgumentParser(description="Test RPC server.")
parser.add_argument(
    '--amqphost', dest='amqphost', action='store',
    default="localhost", help='AMQP broker host.')


class Test:

    def Mul(self, args):
        return args["A"] * args["B"]


async def run(onstop, amqphost):
    transport, protocol = await aioamqp.connect(host=amqphost)
    codec = await amqprpc.server_codec(protocol, "testrpc", amqprpc.Json)
    codec.register(Test())

    await onstop.wait()

    await codec.close()
    await protocol.close()
    transport.close()


if __name__ == '__main__':
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    onstop = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, onstop.set)
    loop.run_until_complete(run(onstop, args.amqphost))