# -*- coding: utf-8 -*-
"""Async RPC library based on AMQP protocol.
"""
import asyncio
import inspect

import counter
import msgpack


class Response(object):
    """Represents a RPC response.
    """

    def __init__(self):
        self.headers = None
        self.body = None


class Request(object):
    """Represents a RPC request.
    """

    def __init__(self, num):
        self.num = num
        self.event = asyncio.Event()
        self.response = Response()


async def register_server(server, name, channel):
    """Consume messages from the channel and handle them using the server.

    Args:
        server: A server that will handle requests.
        name: Server name.
        channel: Async AMQP channel.
    """
    funcs = (i for i in dir(server) if callable(getattr(server, i)))
    calltable = {
        "{0}.{1}".format(name, i): getattr(server, i)
        for i in funcs if not i.startswith("_")
    }

    if callable(server):
        calltable[name] = server

    queue = await channel.queue_declare(queue_name=name)

    async def get_response(body, properties):
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

        func = calltable.get(properties.reply_to)
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

    async def onrequest(channel, body, envelope, properties):
        response = await get_response(body, properties)
        await channel.basic_publish(**response)

    await channel.basic_consume(onrequest, no_ack=True, queue_name=name)


async def register_client(server, channel, timeout=60):
    """Create a client for a server with the name provided.
    """
    requests = {}
    reqcnt = counter.UInt64()

    async def onresponse(channel, body, envelope, properties):
        request = requests.pop(int(properties.message_id), None)
        if request:
            # TODO(vbogretsov): do not create empty dict of headers are None.
            request.response.headers = properties.headers or {}
            if "error" not in request.response.headers:
                request.response.body = msgpack.unpackb(body, encoding="utf-8")
            request.event.set()

    queue = await channel.queue_declare("")
    await channel.basic_consume(
        onresponse, no_ack=True, queue_name=queue["queue"])

    class Client(object):
        def __getattr__(self, name):
            # TODO(vbogretsov): handle __call__.
            reply_to = "{0}.{1}".format(server, name)

            async def call(*args, **kwargs):
                request = Request(reqcnt.inc())
                requests[request.num] = request
                payload = {"a": args, "k": kwargs}

                properties = {
                    "correlation_id": queue["queue"],
                    "reply_to": reply_to,
                    "message_id": str(request.num)
                }

                await channel.basic_publish(
                    exchange_name="",
                    routing_key=server,
                    payload=msgpack.packb(payload),
                    properties=properties)

                await asyncio.wait_for(request.event.wait(), timeout=timeout)

                if "error" in request.response.headers:
                    raise RPCError(request.response.headers["error"])

                return request.response.body

            setattr(self, name, call)
            return call

    return Client()


class RPCError(Exception):
    """Represents a RPC error.
    """
    pass