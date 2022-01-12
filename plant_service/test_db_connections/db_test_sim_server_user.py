# Test for connecting via sim server user.

import MySQLdb as db_client;

print(f'testing sim server user for db...')

with open('../DB_CREDENTIALS.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith("sim_server_user"):
            line = line.rstrip();
            user_name,_, password, database = line.split(",");
db_connection = db_client.connect("localhost",user_name,password,database);

cursor = db_connection.cursor();
cursor.execute("SELECT * FROM tickets");

res = cursor.fetchall();

for index, row in enumerate(res):
    #Rows returned as tuples.
    print(f'row [{index}]: {row}')

db_connection.close();

