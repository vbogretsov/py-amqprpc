# -*- coding:utf-8 -*-
import os
import setuptools
from distutils import core

NAME = "amqprpc"
AUTHOR = "Vladimir Bogretsov"
EMAIL = "bogrecov@gmail.com"
DESCRIPTION = "Async RPC library based on AMQP protocol."
VERSION = "0.1.0"
URL = "https://github.com/vbogretsov/py-amqprpc.git"
LICENCE = "MIT"


counter_module_kwargs = {
    "sources": [
        "counter.c"
    ],
}

atomic = core.Extension("counter", **counter_module_kwargs)

setuptools.setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR,
    py_modules=[NAME],
    ext_modules=[atomic],
    url=URL,
    license=LICENCE,
    install_requires=[
        "msgpack-python"
    ]
)