import asyncio
import logging
import signal
import random

signal.signal(signal.SIGINT, signal.SIG_DFL)

from mysqlproto.protocol import start_mysql_server
from mysqlproto.protocol.base import OK, ERR, EOF
from mysqlproto.protocol.flags import Capability
from mysqlproto.protocol.handshake import (
    HandshakeV10,
    HandshakeResponse41,
    AuthSwitchRequest,
)
from mysqlproto.protocol.query import (
    ColumnDefinition,
    ColumnDefinitionList,
    ResultSet,
    FileReadPacket,
)


async def accept_server(server_reader, server_writer):
    task = asyncio.Task(handle_server(server_reader, server_writer))


async def handle_server(server_reader, server_writer):
    handshake = HandshakeV10()
    handshake.write(server_writer)
    print("Incoming Connection:" + str(server_writer.get_extra_info("peername")[:2]))
    await server_writer.drain()
    switch2clear = False
    handshake_response = await HandshakeResponse41.read(
        server_reader.packet(), handshake.capability
    )
    username = handshake_response.user
    print("Login Username:" + username.decode("ascii"))
    # print("<=", handshake_response.__dict__)
    # 检测是否需要切换到mysql_clear_password
    if username.endswith(b"_clear"):
        switch2clear = True
        username = username[: -len("_clear")]
    capability = handshake_response.capability_effective

    if (
        Capability.PLUGIN_AUTH in capability
        and handshake.auth_plugin != handshake_response.auth_plugin
        and switch2clear
    ):
        print("Switch Auth Plugin to mysql_clear_password")
        AuthSwitchRequest().write(server_writer)
        await server_writer.drain()
        auth_response = await server_reader.packet().read()
        print("<=", auth_response)

    result = OK(capability, handshake.status)
    result.write(server_writer)
    await server_writer.drain()

    while True:
        server_writer.reset()
        packet = server_reader.packet()
        try:
            cmd = (await packet.read(1))[0]
        except Exception as _:
            # TODO:可能会出问题 ┓( ´∀` )┏
            return
            pass
        print("<=", cmd)
        query = await packet.read()
        if query != "":
            query = query.decode("ascii")
            print(query)
        if cmd == 1:
            result = OK(capability, handshake.status)
        elif cmd == 3:
            if "SHOW VARIABLES".lower() in query.lower():
                print("Sending Fake MySQL Server Environment Data")
                ColumnDefinitionList(
                    (ColumnDefinition("d"), ColumnDefinition("e"))
                ).write(server_writer)
                EOF(capability, handshake.status).write(server_writer)
                ResultSet(("max_allowed_packet", "65535")).write(server_writer)
                ResultSet(("system_time_zone", "UTC")).write(server_writer)
                ResultSet(("time_zone", "SYSTEM")).write(server_writer)
                ResultSet(("init_connect", "")).write(server_writer)
                ResultSet(("auto_increment_increment", "1")).write(server_writer)
                result = EOF(capability, handshake.status)
            elif "set".lower() in query.lower():
                # print("Sending Fake MySQL Server Environment Data")
                # ColumnDefinitionList(
                #     (ColumnDefinition("d"), ColumnDefinition("e"))
                # ).write(server_writer)
                # EOF(capability, handshake.status).write(server_writer)
                # ResultSet(("max_allowed_packet", "65535")).write(server_writer)
                # ResultSet(("system_time_zone", "UTC")).write(server_writer)
                # ResultSet(("time_zone", "SYSTEM")).write(server_writer)
                # ResultSet(("init_connect", "")).write(server_writer)
                # ResultSet(("auto_increment_increment", "1")).write(server_writer)
                # result = EOF(capability, handshake.status)
                result = OK(capability, handshake.status)

            elif "SQL_AUTO_IS_NULL".lower() in query.lower():
                result = OK(capability, handshake.status)
            elif query.encode("ascii").decode("ascii") == "select a,b,c from book":
                ColumnDefinitionList(
                    (
                        ColumnDefinition("a"),
                        ColumnDefinition("b"),
                        ColumnDefinition("c"),
                    )
                ).write(server_writer)
                EOF(capability, handshake.status).write(server_writer)
                ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                result = EOF(capability, handshake.status)

            else:
                # yield from process_fileread(
                #     server_reader, server_writer, random.choice(defaultFiles)
                # )
                result = OK(capability, handshake.status)

        else:
            # result = ERR(capability)
            result = OK(capability, handshake.status)

        result.write(server_writer)
        await server_writer.drain()


yso_dict = {"xxx": "xxx"}


logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    f = start_mysql_server(handle_server, host=None, port=3306)
    print("===========================================")
    print("ZshieldSQL")

    print("Start Server at port 3306")
    loop.run_until_complete(f)
    loop.run_forever()
