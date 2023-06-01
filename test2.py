import mysql.connector
from mysql.connector import FieldType
import time

# Connect to server
cnx = mysql.connector.connect(
    host="127.0.0.1", port=3306, user="xxx", password="s3cre3t!"
)

# Get a cursor
cur = cnx.cursor()

# Execute a query
cur.execute("select a,b,c from book")

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
