import mysql.connector
from mysql.connector import FieldType
import time
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
    make_column_def,
)
from mysqlproto.protocol.mysql_constants import FieldFlags


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


gen_mysql_response()
