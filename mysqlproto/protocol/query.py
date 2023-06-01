import asyncio
import struct

from .types import IntLengthEncoded, StringLengthEncoded

# 参照C++版本

# https://github.com/loganlinn/ClickHouse/blob/5f99d887ccc235c6c177ccbf5f96292806f5a0d7/src/Core/MySQLProtocol.h#L43

# enum ColumnType
# {
#     MYSQL_TYPE_DECIMAL = 0x00,
#     MYSQL_TYPE_TINY = 0x01,
#     MYSQL_TYPE_SHORT = 0x02,
#     MYSQL_TYPE_LONG = 0x03,
#     MYSQL_TYPE_FLOAT = 0x04,
#     MYSQL_TYPE_DOUBLE = 0x05,
#     MYSQL_TYPE_NULL = 0x06,
#     MYSQL_TYPE_TIMESTAMP = 0x07,
#     MYSQL_TYPE_LONGLONG = 0x08,
#     MYSQL_TYPE_INT24 = 0x09,
#     MYSQL_TYPE_DATE = 0x0a,
#     MYSQL_TYPE_TIME = 0x0b,
#     MYSQL_TYPE_DATETIME = 0x0c,
#     MYSQL_TYPE_YEAR = 0x0d,
#     MYSQL_TYPE_VARCHAR = 0x0f,
#     MYSQL_TYPE_BIT = 0x10,
#     MYSQL_TYPE_NEWDECIMAL = 0xf6,
#     MYSQL_TYPE_ENUM = 0xf7,
#     MYSQL_TYPE_SET = 0xf8,
#     MYSQL_TYPE_TINY_BLOB = 0xf9,
#     MYSQL_TYPE_MEDIUM_BLOB = 0xfa,
#     MYSQL_TYPE_LONG_BLOB = 0xfb,
#     MYSQL_TYPE_BLOB = 0xfc,
#     MYSQL_TYPE_VAR_STRING = 0xfd,
#     MYSQL_TYPE_STRING = 0xfe,
#     MYSQL_TYPE_GEOMETRY = 0xff
# };
#     void writePayloadImpl(WriteBuffer & buffer) const override
#     {
#         writeLengthEncodedString(std::string("def"), buffer); /// always "def"
#         writeLengthEncodedString(schema, buffer);
#         writeLengthEncodedString(table, buffer);
#         writeLengthEncodedString(org_table, buffer);
#         writeLengthEncodedString(name, buffer);
#         writeLengthEncodedString(org_name, buffer);
#         writeLengthEncodedNumber(next_length, buffer);
#         buffer.write(reinterpret_cast<const char *>(&character_set), 2);
#         buffer.write(reinterpret_cast<const char *>(&column_length), 4);
#         buffer.write(reinterpret_cast<const char *>(&column_type), 1);
#         buffer.write(reinterpret_cast<const char *>(&flags), 2);
#         buffer.write(reinterpret_cast<const char *>(&decimals), 2);
#         writeChar(0x0, 2, buffer);
#     }
# };

import struct
import socket
import warnings
import asynchat
import asyncore

from .mysql_constants import *

"""
Authors: Daniil Sadyrin (http://twitter.com/cyberguru007), Alexey Moskvin
https://github.com/CFandR-github
"""


class Packet:
    def __init__(self):
        pass

    def pack_1_byte(self, v):
        return struct.pack("B", v)

    def pack_2_bytes(self, v):
        return struct.pack("BB", v & 0xFF, v >> 8)

    def pack_3_bytes(self, v):
        return struct.pack("BBB", v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)

    def pack_4_bytes(self, v):
        return struct.pack("I", v)

    def pack(self, nested=True):
        if hasattr(self, "get_to_str"):
            self.data = self.get_to_str()
        else:
            raise Exception("Eror")

        if not nested:
            r = b""
            r += self.pack_3_bytes(len(self.data))
            r += self.pack_1_byte(self.num)
            r += self.data
        else:
            r = self.data
        return r


class LengthEncodedInteger(Packet):
    def __init__(self, value):
        self.value = value

    def get_to_str(self):
        if self.value < 251:
            return self.pack_1_byte(self.value)
        elif self.value >= 251 and self.value < (1 << 16):
            return b"\xfc" + self.pack_2_bytes(self.value)
        elif self.value >= (1 << 16) and self.value < (1 << 24):
            return b"\xfd" + self.pack_3_bytes(self.value)
        elif self.value >= (1 << 24) and self.value < (1 << 64):
            return b"\xfe" + self.pack_4_bytes(self.value)


class LengthEncodedString(Packet):
    def __init__(self, text):
        self.text = text.encode("ascii")

    def get_to_str(self):
        r = LengthEncodedInteger(len(self.text)).pack()
        r += self.text
        return r


class ColumnDefinition1(Packet):
    def __init__(
        self,
        catalog,
        schema,
        table,
        org_table,
        name,
        org_name,
        charsetnr=MysqlCollation.UTF8_GENERAL_CI,
        length=0xFF,
        type_=FieldFlags.FIELD_TYPE_VARCHAR,
        flags=0xFFFF,
        decimals=0,
    ):
        self.catalog = catalog
        self.schema = schema
        self.table = table
        self.org_table = org_table
        self.name = name
        self.org_name = org_name
        self.next_length = 0x0C
        self.charsetnr = charsetnr
        self.length = length
        self.type = type_
        self.flags = flags
        self.decimals = decimals

    def get_to_str(self):
        r = b""
        r += LengthEncodedString(self.catalog).pack()
        r += LengthEncodedString(self.schema).pack()
        r += LengthEncodedString(self.table).pack()
        r += LengthEncodedString(self.org_table).pack()
        r += LengthEncodedString(self.name).pack()
        r += LengthEncodedString(self.org_name).pack()
        r += LengthEncodedInteger(self.next_length).pack()
        r += self.pack_2_bytes(self.charsetnr)
        r += self.pack_4_bytes(self.length)
        r += self.pack_1_byte(self.type)
        r += self.pack_2_bytes(self.flags)
        r += self.pack_1_byte(self.decimals)
        r += b"\x00\x00"
        return r

    def write(self, stream):
        p = self.get_to_str()
        print(p)
        stream.write(p)


def make_column_def(table, name, type, column_flags):
    return ColumnDefinition1(
        "def", "", table, table, name, name, type_=type, flags=column_flags
    )


# https://dev.mysql.com/doc/internals/en/protocoltext-resultset.html
class ColumnDefinition:
    def __init__(self, name, col_type=b"\x0f"):
        self.name = name
        self.col_type = col_type

    def write(self, stream):
        # packet = [
        #     StringLengthEncoded.write(b"def"),  # catalog
        #     StringLengthEncoded.write(b""),  # schema
        #     StringLengthEncoded.write(b"book"),  # table
        #     StringLengthEncoded.write(b"book"),  # org_table
        #     StringLengthEncoded.write(self.name.encode("ascii")),
        #     StringLengthEncoded.write(self.name.encode("ascii")),
        #     b"\x0c",  # filter1
        #     b"\x3f\x00",  # character_set
        #     b"\x1c\x00\x00\x00",  # column_length
        #     # b'\xfc', #column_type
        #     self.col_type,  # column_type
        #     b"\xff\xff",  # flags
        #     b"\x00",  # decimals
        #     b"\x00" * 2,  # filler_2
        # ]

        packet = [
            StringLengthEncoded.write(b"def"),  # catalog
            StringLengthEncoded.write(b""),  # schema
            StringLengthEncoded.write(b"book"),  # table
            StringLengthEncoded.write(b"book"),  # org_table
            StringLengthEncoded.write(self.name.encode("ascii")),
            StringLengthEncoded.write(self.name.encode("ascii")),
            # 12个字节长度
            b"\x0c",  # filter1
            # b"\x3f\x00",  # character_set
            b"\x21\x00",
            b"\x00\x00\x00\xff",  # column_length
            # b'\xfc', #column_type
            self.col_type,  # column_type
            # https://dev.mysql.com/doc/dev/mysql-server/latest/group__group__cs__column__definition__flags.html
            b"\xff\xff",  # flags
            b"\x00",  # decimals
            b"\x00" * 2,  # filler_2
        ]

        p = b"".join(packet)
        print(p)
        stream.write(p)


class ColumnDefinitionList:
    def __init__(self, columns=None):
        self.columns = columns or []

    def write(self, stream):
        p = IntLengthEncoded.write(len(self.columns))

        stream.write(p)

        for i in self.columns:
            i.write(stream)


class FileReadPacket:
    def __init__(self, filename=None):
        self.filename = filename

    def write(self, stream):
        print("reading file:" + self.filename.decode("ascii"))
        # stream.write(p)
        # stream.write(b'\x00\x00\x01')
        stream.write(b"\xfb" + self.filename)


class ResultSet:
    def __init__(self, values):
        self.values = values

    def write(self, stream):
        s = StringLengthEncoded.write

        packet = []

        for i in self.values:
            if i is None:
                packet.append(b"\xfb")
            else:
                if isinstance(i, bytes):
                    packet.append(s(i))
                elif isinstance(i, int):
                    packet.append(IntLengthEncoded.write(i))
                else:
                    packet.append(s(str(i).encode("ascii")))
        p = b"".join(packet)
        stream.write(p)
