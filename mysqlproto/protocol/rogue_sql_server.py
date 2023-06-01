import os
import sys
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
        self.text = text

    def get_to_str(self):
        r = LengthEncodedInteger(len(self.text)).pack()
        r += self.text
        return r


class ColumnDefinition(Packet):
    def __init__(
        self,
        catalog,
        schema,
        table,
        org_table,
        name,
        org_name,
        charsetnr,
        length,
        type_,
        flags,
        decimals,
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


class EOF(Packet):
    def __init__(self, more_results=False):
        self.EOF = 0xFE
        self.warnings = 0
        self.server_status = 0x002 | (0x8 if more_results else 0)

    def get_to_str(self):
        r = b""
        r += self.pack_1_byte(self.EOF)
        r += self.pack_2_bytes(self.warnings)
        r += self.pack_2_bytes(self.server_status)
        return r


class ResultsetRow(Packet):
    def __init__(self, row):
        self.row = row

    def get_to_str(self):
        return b"".join([LengthEncodedString(v).pack() for v in self.row])


class COM_QUERY_RESPONSE(Packet):
    def __init__(self, responce):
        # ProtocolText::Resultset
        self.responce = responce

    def get_to_str(self):
        resp_str = b""
        total_num = 1
        try:
            for i, resp in enumerate(self.responce):
                self.column_count, self.column_def, self.rows = resp

                r = b""
                arr = []
                arr.append(LengthEncodedInteger(self.column_count))
                for c in self.column_def:
                    arr.append(ColumnDefinition(*c))
                arr.append(EOF())
                for row in self.rows:
                    arr.append(ResultsetRow(row))
                arr.append(
                    EOF(more_results=(True if i != len(self.responce) - 1 else False))
                )

                for p in arr:
                    p.num = total_num
                    total_num += 1
                    r += p.pack(nested=False)
                resp_str += r
        except Exception as e:
            print(e)
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))

        return resp_str


class COM_QUIT(Packet):
    def __init__(self):
        self.cmd = 0x1

    def get_to_str(self):
        return self.pack_1_byte(self.cmd)


class COM_SET_OPTION(Packet):
    def __init__(self):
        self.com_set_option = 0x1B
        self.option_operation = 0

    def get_to_str(self):
        return self.pack_1_byte(self.com_set_option) + self.pack_1_byte(
            self.option_operation
        )


class PacketOK(Packet):
    def __init__(self):
        self.header = 0
        self.affected_rows = 0
        self.last_insert_id = 0
        self.status_flags = 0x2
        self.warnings = 0

    def get_to_str(self):
        r = b""
        r += self.pack_1_byte(self.header)
        r += LengthEncodedInteger(self.affected_rows).pack()
        r += LengthEncodedInteger(self.last_insert_id).pack()
        r += self.pack_2_bytes(self.status_flags)
        r += self.pack_2_bytes(self.warnings)
        return r


class AuthSwitch(Packet):
    def __init__(self):
        self.status = 0xFE
        self.auth_method_name = "mysql_clear_password"
        self.auth_method_data = "abc"

    def get_to_str(self):
        r = b""
        r += self.pack_1_byte(self.status)
        r += self.auth_method_name + "\x00"
        r += self.auth_method_data + "\x00"
        return r


class Handshake(Packet):
    def __init__(
        self,
        protocol_version,
        server_version,
        connection_id,
        auth_plugin_data_part_1,
        capability_flag_1,
        character_set,
        status_flags,
        capability_flags_2,
        auth_plugin_data_len,
        auth_plugin_data_part_2,
        auth_plugin_name,
    ):
        self.protocol_version = protocol_version
        self.server_version = server_version
        self.connection_id = connection_id
        self.auth_plugin_data_part_1 = auth_plugin_data_part_1
        self.filler = 0
        self.capability_flag_1 = capability_flag_1
        self.character_set = character_set
        self.status_flags = status_flags
        self.capability_flags_2 = capability_flags_2
        self.auth_plugin_data_len = auth_plugin_data_len
        self.auth_plugin_data_part_2 = auth_plugin_data_part_2
        self.auth_plugin_name = auth_plugin_name

    def get_to_str(self):
        r = b""
        r += self.pack_1_byte(self.protocol_version)
        r += self.server_version + b"\x00"
        r += self.pack_4_bytes(self.connection_id)
        r += self.auth_plugin_data_part_1
        r += self.pack_1_byte(self.filler)
        r += self.pack_2_bytes(self.capability_flag_1)
        r += self.pack_1_byte(self.character_set)
        r += self.pack_2_bytes(self.status_flags)
        r += self.pack_2_bytes(self.capability_flags_2)
        r += self.pack_1_byte(self.auth_plugin_data_len)
        r += b"\x00" * 10
        r += self.auth_plugin_data_part_2
        r += self.pack_1_byte(self.filler)
        r += self.auth_plugin_name
        r += b"\x00"
        return r
