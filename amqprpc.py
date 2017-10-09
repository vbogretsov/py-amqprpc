# -*- coding: utf-8 -*-
"""Async RPC library based on AMQP protocol.
"""
import asyncio
import inspect

import counter
import msgpack


def _nameof(obj):
    return obj.__name__ if hasattr(obj, "__name__") else obj.__class__.__name__


async def _get_response(callables, body, properties):
    if properties.reply_to is None:
        raise ValueError("properties.reply_to cannot be None")

    response = {
        "exchange_name": "",
        "routing_key": properties.correlation_id,
        "properties": {
            "correlation_id": properties.correlation_id,
            "message_id": properties.message_id,
            "reply_to": properties.reply_to
        }
    }

    func = callables.get(properties.reply_to)
    payload = None

    if func:
        request = msgpack.unpackb(body, encoding="utf-8")
        try:
            if inspect.iscoroutinefunction(func):
                payload = await func(*request["a"], **request["k"])
            else:
                payload = func(*request["a"], **request["k"])
        except Exception as ex:
            response["properties"]["headers"] = {"error": str(ex)}
    else:
        response["properties"]["headers"] = {
            "error": "unknown function {0}".format(properties.reply_to)
        }

    response["payload"] = msgpack.packb(payload or {})
    return response


async def server_codec(connection, name):
    channel = await connection.channel()
    codec = _ServerCodec(channel)

    async def onrequest(channel, body, envelope, properties):
        response = await _get_response(codec.callables, body, properties)
        await channel.basic_publish(**response)

    await channel.queue_declare(queue_name=name)
    await channel.basic_consume(onrequest, no_ack=True, queue_name=name)
    return codec


async def client_codec(connection, name):
    channel = await connection.channel()
    queue = await channel.queue_declare("")
    codec = _ClientCodec(channel, name, queue["queue"])

    async def onresponse(channel, body, envelope, properties):
        request = codec.reqgen.requests.pop(int(properties.message_id), None)
        if request:
            # TODO(vbogretsov): do not create empty dict if headers are None.
            request.response.headers = properties.headers or {}
            if "error" not in request.response.headers:
                request.response.body = msgpack.unpackb(body, encoding="utf-8")
            request.event.set()

    await channel.basic_consume(
        onresponse, no_ack=True, queue_name=queue["queue"])

    return codec


class _RequestGenerator(object):
    """Rperesents a request generator.
    """
    def __init__(self):
        self.requests = {}
        self.counter = counter.UInt64()

    # NOTE(vbogretsov): CQRS violation.
    def __call__(self):
        num = self.counter.inc()
        req = _Request(num)
        self.requests[num] = req
        return req


class _Response(object):
    """Represents a RPC response.
    """

    def __init__(self):
        self.headers = None
        self.body = None


class _Request(object):
    """Represents a RPC request.
    """

    def __init__(self, num):
        self.num = num
        self.event = asyncio.Event()
        self.response = _Response()


class _Codec(object):
    """Base codec.
    """
    def __init__(self, channel):
        self.channel = channel

    async def close(self):
        await self.channel.close()


class _ServerCodec(_Codec):
    """Represents a server RPC codec.
    """
    def __init__(self, channel):
        super(_ServerCodec, self).__init__(channel)
        self.callables = {}

    def register(self, server):
        name = _nameof(server)

        if callable(server):
            self.callables[name] = server

        methods = (i for i in dir(server) if callable(getattr(server, i)))

        for method in methods:
            if not method.startswith("_"):
                fullname = "{0}.{1}".format(name, method)
                self.callables[fullname] = getattr(server, method)


class _ClientCodec(_Codec):
    """Represents a client RPC codec.
    """
    def __init__(self, channel, routing_key, correlation_id):
        super(_ClientCodec, self).__init__(channel)
        self.routing_key = routing_key
        self.correlation_id = correlation_id
        self.reqgen = _RequestGenerator()

    def client(self, server_name):
        return _Client(
            server_name, self.channel, self.reqgen,
            self.routing_key, self.correlation_id)


class _Client(object):
    """Represents a client.
    """
    def __init__(self, srvname, channel, reqgen, routing_key, correlation_id):
        self.srvname = srvname
        self.channel = channel
        self.reqgen = reqgen
        self.routing_key = routing_key
        self.correlation_id = correlation_id

    def __getattr__(self, name):
        reply_to = "{0}.{1}".format(self.srvname, name)

        async def call(*args, **kwargs):
            request = self.reqgen()

            payload = {"a": args, "k": kwargs}

            properties = {
                "correlation_id": self.correlation_id,
                "reply_to": reply_to,
                "message_id": str(request.num)
            }

            await self.channel.basic_publish(
                exchange_name="",
                routing_key=self.routing_key,
                payload=msgpack.packb(payload),
                properties=properties)

            await asyncio.wait_for(request.event.wait(), timeout=60)

            if "error" in request.response.headers:
                raise RPCError(request.response.headers["error"])

            return request.response.body

        setattr(self, name, call)
        return call


class RPCError(Exception):
    """Represents a RPC error.
    """
    pass