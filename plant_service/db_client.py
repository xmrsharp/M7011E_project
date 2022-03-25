

import MySQLdb as db
from datetime import datetime
#TODO Change hardcoaded db name to loadenv.
#TODO Fidn suitable way of connecting/disconnecting without dis/conn on each db call -> no connect/ds = error after inactivity, else expensive to constantly create new connection etc.
#TODO refactor as mysqldb can return result as dic.
class PowerPlantDBClient():
    def __init__(self, db_user, pw, host='localhost'):#, db_name='power_plants'):
        self.host = host
        self.db_user = db_user
        self.pw = pw
        self.db_connection = db.connect(self.host,self.db_user,self.pw,'power_plants');#self.database_name);
    

    def open_connection(self):
        self.db_connection = db.connect(self.host, self.db_user, self.pw, 'power_plants')

    def close_connection(self):
        self.db_connection.close()

    def check_query_injection(self,query):
        pass

    #TODO Delete with a fresh set of eyes so i know that they are not needed.
    #def get_plants(self, plant_ids):
        ####### USED FOR TESTING ########
    #    if plant_ids=="TESTING":
    #        cursor = self.db_connection.cursor()
    #        cursor.execute(f'SELECT * FROM prosumers;')
    #        res = cursor.fetchall()
    #        self.db_connection.commit()
    #        return res
    #    ####### USED FOR TESTING ########
    #    #Should only be called by auth server for loading graph.
    #    plant_string ="plant_id="
    #    prep_stmnt = ""
    #    for plant_id in plant_ids:
    #        prep_stmnt+= plant_string+str(plant_id)+' OR '
    #    prep_stmnt = prep_stmnt.rstrip(' OR ')
    #    cursor = self.db_connection.cursor()
    #    cursor.execute(f'SELECT * FROM prosumers WHERE {prep_stmnt}')
    #    res = cursor.fetchall()
    #    self.db_connection.commit()
    #    return res


    def get_plant_storage(self,plant_id):
        #self.open_connection();
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT stored_charge FROM prosumers where plant_id={plant_id}')
        plant_stored_power = cursor.fetchone()[0]
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return plant_stored_power;

    # Returns wind speed in m/s and temperature in celcius. 
    def get_current_weather(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT wind_speed,temperature from weather ORDER BY time_sampled DESC LIMIT 1;')
        wind_speed, temperature = cursor.fetchone()
        self.db_connection.commit() # Update db to sync changes to all calls.
        #self.close_connection()
        cursor.close()
        return (wind_speed, temperature)

    # Insert new log of current weather conditions
    def update_weather(self, new_wind_speed, new_temperature):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute(f'INSERT INTO weather(wind_speed, temperature) VALUES({new_wind_speed},{new_temperature})')
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()

    # Returns current price per w/h
    def get_price(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT price FROM price_history ORDER BY time_sampled DESC LIMIT 1;')
        price = cursor.fetchone()[0]
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return price

    # Insert log of current w/h price
    def update_price(self, new_price_value):
        #self.open_connection()
        cursor = self.db_connection.cursor();
        cursor.execute(f'INSERT INTO price_history(price) VALUES({new_price_value})')
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()

    # TODO if there is time refactor to give sim its own db_client of a different type than this one.
    # TODO change query when complete.
    def get_updated_plant_storage(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        #cursor.execute('SELECT plant_id, (current_production-current_consumption+stored_charge) FROM prosumers WHERE active=TRUE;')
        cursor.execute('SELECT plant_id, (current_production-current_consumption+stored_charge) FROM prosumers')
        res = cursor.fetchall()
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return res

    def get_net_storage(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        #cursor.execute("SELECT SUM(current_production)-SUM(current_consumption)+SUM(stored_charge) FROM prosumers WHERE ACTIVE=TRUE;") 
        cursor.execute("SELECT SUM(current_production)-SUM(current_consumption)+SUM(stored_charge) FROM prosumers")
        res = cursor.fetchone()[0]
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return res
    
    #Returns a list of all valid plant_ids related to token.
    def get_plant_related_token(self,token,plant_ids):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute()
        res = cursor.fetchall()
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return res

    def update_plant_storage(self, plant_id, updated_plant_storage):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET stored_charge={updated_plant_storage} WHERE plant_id={plant_id};')
        res = cursor.fetchone()
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()

    def get_active_plants(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT plant_id FROM prosumers WHERE active=TRUE')
        res = cursor.fetchall()
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return res
    
    def admin_get_plants(self):
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT * FROM prosumers;')
        all_plants = cursor.fetchall()
        self.db_connection.commit()
        cursor.close()
        return all_plants

    def get_plants(self, requested_plants):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        prep_stmnt = self.plant_or_string(requested_plants)
        cursor.execute(f'SELECT * FROM prosumers WHERE ({prep_stmnt})')
        requested_plants = cursor.fetchall() 
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return requested_plants

    # OK AND USED
    def plant_or_string(self, plants):
        #self.open_connection()
        plant_string ="plant_id="
        prep_stmnt = ""
        for plant_id in plants:
            prep_stmnt+= plant_string+str(plant_id)+' OR '
        prep_stmnt = prep_stmnt.rstrip(' OR ')
        #self.close_connection()
        #cursor.close()
        return prep_stmnt

    # OK AND USED
    def shutdown_plant(self, plant_ids):
        #self.open_connection()
        plant_string = self.plant_or_string(plant_ids)
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET active=0 WHERE {plant_string};')
        #cursor.execute(f'UPDATE prosumers AS P INNER JOIN tickets AS T ON P.plant_id=T.plant_id SET active=0 WHERE P.plant_id={plant_id} AND T.token="{auth_ticket}" AND T.token_expires > DATE(NOW());')
        self.db_connection.commit();
        #self.close_connection()
        cursor.close()
    # OK AND USED
    def activate_plant(self, plant_ids):
        #self.open_connection()
        plant_string = self.plant_or_string(plant_ids)
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET active=1 WHERE {plant_string};')
        #cursor.execute(f'UPDATE prosumers AS P INNER JOIN tickets AS T ON P.plant_id=T.plant_id SET active=1 WHERE P.plant_id={plant_id} AND T.token="{auth_ticket}" AND T.token_expires > DATE(NOW());')
        self.db_connection.commit();
        #self.close_connection()
        cursor.close()

    # Used for authenticating incoming request. 
    def get_ticket_validity(self, ticket):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT P.plant_id FROM prosumers AS P INNER JOIN tickets AS T ON P.plant_id=T.plant_id WHERE T.token="{ticket}" AND T.token_expires > NOW();')
        ticket_plants = cursor.fetchall()
        self.db_connection.commit()
        access_nodes = []
        for plant in ticket_plants:
            access_nodes.append(str(plant[0]))
        #self.close_connection()
        cursor.close()
        return (len(access_nodes)>0), access_nodes


    # Return connected plants to valid token. Some misuse here.
    def get_token_valid(self, token, requested_plants):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT plant_id FROM tickets WHERE token="{token}" AND token_expires>NOW();')
        res = cursor.fetchall()
        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return res

    # Return expiration date of token. OK method.
    def get_ticket_expiration(self, token):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT token_expires FROM tickets WHERE token="{token}"')
        expiration_time = cursor.fetchone()
        if expiration_time is not None:
            expiration_time = expiration_time[0]

        self.db_connection.commit()
        #self.close_connection()
        cursor.close()
        return expiration_time

    # To be used by plant engine, cleanup old tokens.
    def remove_token_expire(self):
        #self.open_connection()
        cursor = self.db_connection.cursor()
        #Insert token for admin if we want admins to be superuser, else just set the admin token to never expire.
        cursor.execute(f'DELETE FROM tickets WHERE token_expires<DATE(NOW());')
        self.db_connection.commit()
        cursor.close()
        #self.close_connection()

