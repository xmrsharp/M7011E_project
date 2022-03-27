# Test for connecting via sim user.

import MySQLdb as db_client;

print(f'testing sim user for db...')

with open("../DB_CREDENTIALS.txt", 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith("sim_user"):
            line = line.rstrip();
            user_name,_, password, database = line.split(",");
db_connection = db_client.connect("localhost",user_name,password,database);

cursor = db_connection.cursor();
cursor.execute("SELECT token FROM tickets WHERE plant_id=4");

res = cursor.fetchall();
print(f'res without enumerating : {res[0][0]}')
for index, row in enumerate(res):
    #Rows returned as tuples.
    print(f'row [{index}]: {row}')

db_connection.close();
