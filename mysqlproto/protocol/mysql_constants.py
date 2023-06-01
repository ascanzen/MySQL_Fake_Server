"""
Authors: Daniil Sadyrin (http://twitter.com/cyberguru007), Alexey Moskvin
https://github.com/CFandR-github
"""


class FieldFlags:
    FIELD_TYPE_DECIMAL = 0x00
    FIELD_TYPE_TINY = 0x01
    FIELD_TYPE_SHORT = 0x02
    FIELD_TYPE_LONG = 0x03
    FIELD_TYPE_FLOAT = 0x04
    FIELD_TYPE_DOUBLE = 0x05
    FIELD_TYPE_NULL = 0x06
    FIELD_TYPE_TIMESTAMP = 0x07
    FIELD_TYPE_LONGLONG = 0x08
    FIELD_TYPE_INT24 = 0x09
    FIELD_TYPE_DATE = 0x0A
    FIELD_TYPE_TIME = 0x0B
    FIELD_TYPE_DATETIME = 0x0C
    FIELD_TYPE_YEAR = 0x0D
    FIELD_TYPE_NEWDATE = 0x0E
    FIELD_TYPE_VARCHAR = 0x0F
    FIELD_TYPE_BIT = 0x10
    FIELD_TYPE_NEWDECIMAL = 0xF6
    FIELD_TYPE_ENUM = 0xF7
    FIELD_TYPE_SET = 0xF8
    FIELD_TYPE_TINY_BLOB = 0xF9
    FIELD_TYPE_MEDIUM_BLOB = 0xFA
    FIELD_TYPE_LONG_BLOB = 0xFB
    FIELD_TYPE_BLOB = 0xFC
    FIELD_TYPE_VAR_STRING = 0xFD
    FIELD_TYPE_STRING = 0xFE
    FIELD_TYPE_GEOMETRY = 0xFF


class MysqlFlags:
    NOT_NULL_FLAG = 0x1
    PRI_KEY_FLAG = 0x2
    UNIQUE_KEY_FLAG = 0x4
    MULTIPLE_KEY_FLAG = 0x8
    BLOB_FLAG = 0x10
    UNSIGNED_FLAG = 0x20
    ZEROFILL_FLAG = 0x40
    BINARY_FLAG = 0x80
    ENUM_FLAG = 0x100
    AUTO_INCREMENT_FLAG = 0x200
    TIMESTAMP_FLAG = 0x400
    SET_FLAG = 0x800


class MysqlCollation:
    LATIN1_SWEDISH_CI = 0x08
    UTF8_GENERAL_CI = 0x21
    BINARY = 0x3F
