import mysql.connector
from mysql.connector import FieldType
import time

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

for i in range(len(cur.description)):
    print("Column {}:".format(i + 1))
    desc = cur.description[i]
    print("  column_name = {}".format(desc[0]))
    print("  type = {} ({})".format(desc[1], FieldType.get_info(desc[1])))
    print("  null_ok = {}".format(desc[6]))
    print("  column_flags = {}".format(desc[7]))

# # Fetch one result
row = cur.fetchall()
print("Current date is: {0}".format(row))

# Close connection
cnx.close()
