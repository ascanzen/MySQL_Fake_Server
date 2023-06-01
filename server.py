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
    ColumnDefinition1,
    ColumnDefinitionList,
    ResultSet,
    FileReadPacket,
    make_column_def,
)
from mysqlproto.protocol.mysql_constants import FieldFlags

import mysql.connector
from mysql.connector import FieldType


def gen_mysql_response():
    # Connect to server
    cnx = mysql.connector.connect(
        host="192.168.9.240",
        port=3306,
        user="iotServer",
        password="8o2hm6hNQx4LZBKJ",
        database="iot_server_new",
    )

    # Get a cursor
    cur = cnx.cursor()

    # Execute a query
    cur.execute("select name,bio from authors")

    columns = ColumnDefinitionList()
    results = []

    for i in range(len(cur.description)):
        print("Column {}:".format(i + 1))
        desc = cur.description[i]
        print("  column_name = {}".format(desc[0]))
        print("  type = {} ({})".format(desc[1], FieldType.get_info(desc[1])))
        print("  null_ok = {}".format(desc[6]))
        print("  column_flags = {}".format(desc[7]))

        columns.columns.append(
            make_column_def(
                "book",
                "a",
                FieldFlags.FIELD_TYPE_VARCHAR,
                column_flags=0xFFFF,
            ),
        )

    # # Fetch one result
    rows = cur.fetchall()
    # print("Current date is: {0}".format(rows))
    for row in rows:
        print(row)
        results.append(ResultSet(row))

    # Close connection
    cnx.close()

    return columns, results


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
            elif query.encode("ascii").decode("ascii") in [
                "select name,bio from authors",
                "select a,b,c from book",
            ]:
                # ColumnDefinitionList(
                #     (
                #         make_column_def(
                #             "book",
                #             "a",
                #             FieldFlags.FIELD_TYPE_VARCHAR,
                #             column_flags=0xFFFF,
                #         ),
                #         make_column_def(
                #             "book",
                #             "b",
                #             FieldFlags.FIELD_TYPE_VARCHAR,
                #             column_flags=0xFFFF,
                #         ),
                #         make_column_def(
                #             "book",
                #             "c",
                #             FieldFlags.FIELD_TYPE_VARCHAR,
                #             column_flags=0xFFFF,
                #         ),
                #     )
                # ).write(server_writer)
                # EOF(capability, handshake.status).write(server_writer)
                # ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                # ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                # ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                # ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                # ResultSet(("cochran", "asset pricing", "CN123456")).write(server_writer)
                # result = EOF(capability, handshake.status)

                columns, result_set = gen_mysql_response()
                columns.write(server_writer)
                EOF(capability, handshake.status).write(server_writer)
                for r in result_set:
                    r.write(server_writer)
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
