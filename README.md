# py-amqprpc

Async RPC library based on AMQP protocol.

This library allows easy integration with [go-amqprpc](https://github.com/vbogretsov/go-amqprpc).
Clients or servers written in `go-amqprpc` can interact with clients or servers
written in `py-amqprpc`. See [examples](https://github.com/vbogretsov/py-amqprpc/tree/master/examples)
for more details.

## Usage

### Server

A python class or function can be used as RPC server. For this purpose it
should be registered using an instance of `server_codec` (the name comes from
golang net/rpc library).

Let's assume we have the following python class:

```python
class Server:

    def mul(self, args):
        return args["A"] * args["B"]
```

And we are going to use it as RPC server. To do that we should connect AMQP
broker, create server codec and register instance of this class in the codec.

```python
import aioamqp

async def example_server(**amqp_settings):
    transport, protocol = await aioamqp.connect(**amqp_settings)
    codec = await amqprpc.server_codec(protocol, "testrpc", amqprpc.Json)
    codec.register(Server())
    # Now server is regisered and can accept requests to the method `mul`.
    # Codec should be closed before function exits.
```

**NOTE:** this example uses the library [aioamqp](https://github.com/Polyconseil/aioamqp)
but `py-amqprpc` can work with other async AMQP implementation so `aioamqp`
will not be installed as `py-amqprpc` dependency.

Here `testrpc` is the routing key that will be used for routing requests to
services registered in the codec. The parameter `amqprpc.Json` specifies that
messages should be encoded in JSON. See [Messages format](### Messages format)
for more details.

When a class instance is registered all its public methods will be available
for remote call. But either class method or function should accept only 1
argument. Such interface make interopability with services in other languages
more easy.

### Client

To make requests to RPC server we have to create a client instance. Let's
assume we should like to the remote method `mul` of the class `Server` from the
previous example. To do that we should connect AMQP broker, create client codec
and create a client - proxy for the remote instance of the `Server` class.

```python
async def example_client(**amqp_settings):
    transport, protocol = await aioamqp.connect(**amqp_settings)
    codec = await amqprpc.client_codec(protocol, "testrpc", amqprpc.Json)
    client = codec.client("Server")

    try:
        result = client.Mul({"A": 2, "B": 3})
        print(result)
    except amqprpc.RPCError as ex:
        print(ex)
```

Mind the second and third arguments of the function `client_codec`. They should
be the same as in the server.

The argument of the method `client.codec` is the name of the RPC service.
If RPC service is registered as a class isntance, it will be the class name, if
it's registered as a function, it will be the function name.

### Messages format

The `py-amqprpc` allows to specify how RPC requests and responses should be
encoded. The argument `formatter` of the functions `server_codec`,
`client_codec` should be an object with the following methods:

```python

class SomeFormatter:

    def pack(pyobj):
        # Translate python object to the binary representation.

    def unpack(binrepr):
        # Translate binary representation to the python object.
```

The `py-amqprpc` library provides 2 default implementations:
 * `Json` - JSON formatter
 * `MsgPack` - msgpack formatter

## Licence

See the [LICENCE](https://github.com/vbogretsov/py-amqprpc/blob/master/LICENSE) file.
