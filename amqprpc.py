# -*- coding: utf-8 -*-
"""Async RPC library based on AMQP protocol.
"""
import asyncio
import inspect
import json

import counter
import msgpack


async def server_codec(connection, name, formatter):
    """Create RPC server codec.

    The codec can be used to register a service which can be a class or a
    function. The function or a class method should accept only 1 argument to
    be a service endpoint. This approach was choosen to mimic golang net/rpc
    library for easy integration with it.

    Args:
        connection: AMQP connection.
        name: Codec name is used for routing messages to services registered
            in the codec.
        formatter: Contains methods pack(data) and unpack(data) to translate
            a python object to/from bynary representation.

    Returns:
        RPC server codec.
    """
    channel = await connection.channel()
    codec = _ServerCodec(channel)

    async def onrequest(channel, body, envelope, properties):
        response = await _get_response(codec.callables, body, properties,
                                       formatter)
        await channel.basic_publish(**response)

    await channel.queue_declare(queue_name=name)
    await channel.basic_consume(onrequest, no_ack=True, queue_name=name)

    return codec


async def client_codec(connection, name, formatter):
    """Create RPC client codec.

    The codec can be used to create RPC clients.

    Args:
        connection: AMQP connection.
        name: Codec name is used for routing messages to services registered
            in the codec.
        formatter: Contains methods pack(data) and unpack(data) to translate
            a python object to/from bynary representation.

    Returns:
        RPC client codec.

    """
    channel = await connection.channel()
    queue = await channel.queue_declare("")
    codec = _ClientCodec(channel, name, queue["queue"], formatter)

    async def onresponse(channel, body, envelope, properties):
        request = codec.reqgen.requests.pop(int(properties.message_id), None)
        if request:
            request.response.headers = properties.headers or {}
            if "error" not in request.response.headers:
                request.response.body = formatter.unpack(body)
            request.event.set()

    await channel.basic_consume(
        onresponse, no_ack=True, queue_name=queue["queue"])

    return codec


async def _get_response(callables, body, properties, formatter):
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
    result = None

    if func:
        args = formatter.unpack(body)
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(args)
            else:
                result = func(args)
        except Exception as ex:
            response["properties"]["headers"] = {"error": str(ex)}
    else:
        response["properties"]["headers"] = {
            "error": "unknown function {0}".format(properties.reply_to)
        }

    response["payload"] = formatter.pack(result)
    return response


class MsgPack:
    """Represents msgpack format provider.
    """

    @staticmethod
    def pack(data):
        return msgpack.packb(data)

    @staticmethod
    def unpack(data):
        return msgpack.unpackb(data, encoding="utf-8")


class Json:
    """Represents json format provider.
    """

    @staticmethod
    def pack(data):
        return json.dumps(data)

    @staticmethod
    def unpack(data):
        return json.loads(data, encoding="utf-8")


class _RequestGenerator:
    """Rperesents request generator.
    """

    def __init__(self):
        self.requests = {}
        self.counter = counter.UInt64()

    def __call__(self):
        num = self.counter.inc()
        req = _Request(num)
        self.requests[num] = req
        return req


class _Response:
    """Represents RPC response.
    """

    def __init__(self):
        self.headers = None
        self.body = None


class _Request:
    """Represents RPC request.
    """

    def __init__(self, num):
        self.num = num
        self.event = asyncio.Event()
        self.response = _Response()


# TODO(vbogretsov): consider using of conext manager interface.
class _Codec:
    """Base codec.
    """

    def __init__(self, channel):
        self.channel = channel

    async def close(self):
        if self.channel.is_open:
            await self.channel.close()


class _ServerCodec(_Codec):
    """Represents server RPC codec.
    """

    def __init__(self, channel):
        super(_ServerCodec, self).__init__(channel)
        self.callables = {}

    def register(self, server):
        name = getattr(server, "__name__", server.__class__.__name__)

        if callable(server):
            self.callables[name] = server

        methods = (i for i in dir(server) if callable(getattr(server, i)))

        for method in methods:
            # TODO(vbogretsov): check function is callable and has 1 argument.
            if not method.startswith("_"):
                fullname = "{0}.{1}".format(name, method)
                self.callables[fullname] = getattr(server, method)


class _ClientCodec(_Codec):
    """Represents client RPC codec.
    """

    def __init__(self, channel, routing_key, correlation_id, formatter):
        super(_ClientCodec, self).__init__(channel)
        self.routing_key = routing_key
        self.correlation_id = correlation_id
        self.reqgen = _RequestGenerator()
        self.formatter = formatter

    def client(self, server_name):
        return _Client(server_name, self.channel, self.reqgen,
                       self.routing_key, self.correlation_id, self.formatter)


class _Client:
    """Represents RPC client.
    """

    def __init__(self, srvname, channel, reqgen, routing_key, correlation_id,
                 formatter):
        self.srvname = srvname
        self.channel = channel
        self.reqgen = reqgen
        self.routing_key = routing_key
        self.correlation_id = correlation_id
        self.formatter = formatter

    def __getattr__(self, name):
        reply_to = "{0}.{1}".format(self.srvname, name)

        async def call(args):
            request = self.reqgen()

            properties = {
                "correlation_id": self.correlation_id,
                "reply_to": reply_to,
                "message_id": str(request.num)
            }

            await self.channel.basic_publish(
                exchange_name="",
                routing_key=self.routing_key,
                payload=self.formatter.pack(args),
                properties=properties)

            await asyncio.wait_for(request.event.wait(), timeout=60)

            if "error" in request.response.headers:
                raise RPCError(request.response.headers["error"])

            return request.response.body

        setattr(self, name, call)
        return call


class RPCError(Exception):
    """Represents RPC error.
    """
    pass