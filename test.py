import mysql.connector
import time

# Connect to server
cnx = mysql.connector.connect(
    host="127.0.0.1", port=3306, user="xxx", password="s3cre3t!"
)

# Get a cursor
cur = cnx.cursor()

# Execute a query
cur.execute("select 1")

# # Fetch one result
row = cur.fetchone()
print("Current date is: {0}".format(row[0]))

# time.sleep(1000)
# Close connection
cnx.close()
