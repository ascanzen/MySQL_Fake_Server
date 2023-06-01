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
