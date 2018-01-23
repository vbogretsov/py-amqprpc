# -*- coding: utf-8 -*-

def pytest_addoption(parser):
    parser.addoption(
        "--amqp-host",
        action="store",
        dest="amqphost",
        default="localhost",
        help="AMQP broker host")
    parser.addoption(
        "--amqp-port",
        action="store",
        dest="amqpport",
        default="5672",
        help="AMQP broker port")
    parser.addoption(
        "--amqp-user",
        action="store",
        dest="amqpuser",
        default="guest",
        help="AMQP broker user")
    parser.addoption(
        "--amqp-password",
        action="store",
        dest="amqppassword",
        default="guest",
        help="AMQP broker password")
    parser.addoption(
        "--nserver",
        action="store",
        dest="nserver",
        default=1,
        type=int,
        help="number of tests servers")
    parser.addoption(
        "--nclient",
        action="store",
        dest="nclient",
        default=1,
        type=int,
        help="number of tests clients")
    parser.addoption(
        "--ncalls",
        action="store",
        dest="ncalls",
        default=1,
        type=int,
        help="number of server calls per client")
