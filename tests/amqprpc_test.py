# -*- coding: utf-8 -*-
import random
import time

import aioamqp
import pytest

import amqprpc

ROUTING = "amqptest"


class Serv:

    def mul(self, args):
        return {"a": args["a"], "b": args["b"], "mul": args["a"] * args["b"]}


@pytest.fixture
def rng():
    random.seed(time.time())
    return lambda: random.randint(0, 100)


@pytest.fixture
def amqpconnection(request, event_loop):
    transport, protocol = event_loop.run_until_complete(aioamqp.connect(
        host=request.config.option.amqphost,
        port=request.config.option.amqpport,
        login=request.config.option.amqpuser,
        password=request.config.option.amqppassword))

    def fin():
        event_loop.run_until_complete(protocol.close())
        transport.close()

    request.addfinalizer(fin)
    return protocol

@pytest.fixture
def amqpservers(request, amqpconnection, event_loop):
    codecs = []
    for i in range(request.config.option.nserver):
        codec = event_loop.run_until_complete(
            amqprpc.server_codec(amqpconnection, ROUTING, amqprpc.MsgPack))
        codec.register(Serv())
        codecs.append(codec)

    def fin():
        for codec in codecs:
            event_loop.run_until_complete(codec.close())

    request.addfinalizer(fin)
    return codecs


@pytest.fixture
def amqpclients(request, amqpconnection, amqpservers, event_loop):
    codecs = []
    clients = []
    for i in range(request.config.option.nclient):
        codec = event_loop.run_until_complete(
            amqprpc.client_codec(amqpconnection, ROUTING, amqprpc.MsgPack))
        codecs.append(codec)
        clients.append(codec.client("Serv"))

    def fin():
        for codec in codecs:
            event_loop.run_until_complete(codec.close())

    request.addfinalizer(fin)
    return clients


@pytest.mark.asyncio
async def test_ncalls(request, amqpclients, rng, event_loop):
    tasks = []
    for i in range(request.config.option.ncalls):
        for client in amqpclients:
            args = {"a": rng(), "b": rng()}
            tasks.append(event_loop.create_task(client.mul(args)))
    for task in tasks:
        res = await task
        assert res == {"a": res["a"], "b": res["b"], "mul": res["a"] * res["b"]}
 