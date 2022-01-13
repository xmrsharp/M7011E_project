

import MySQLdb as db


#TODO refactor as this class is not doing what it should be doin
class PowerPlantDBClient():
    #Makes no sense to allow another db_name other than power_plants as this specific db_client is used for specific tables.
    def __init__(self, db_user, pw, host='localhost'):#, db_name='power_plants'):
        self.host = host
        self.db_user = db_user
        self.pw = pw
        # TODO Try connection. ERROR WHEN IM OPPENING AND CLOSING CONNECTION TO DB CONSTANTLY.
        self.db_connection = db.connect(self.host,self.db_user,self.pw,'power_plants');#self.database_name);
    

    def open_connection(self):
        self.db_connection = db.connect(self.host, self.db_user, self.pw, 'power_plants')

    def close_connection(self):
        self.db_connection.close()


    def query_db(self, query):
        #if self.check_query_injection(query):
        #
        #    return
        #Report attempt at injection.
        pass

    def check_query_injection(self,query):
        pass


    def get_plants(self, plant_ids):
        plant_string ="plant_id="
        prep_stmnt = ""
        for plant_id in plant_ids:
            prep_stmnt+= plant_string+str(plant_id)+' OR '
        prep_stmnt = prep_stmnt.rstrip(' OR ')
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT * FROM prosumers WHERE {prep_stmnt}')
        res = cursor.fetchall()
        self.db_connection.commit()
        return res


    def get_plant_storage(self,plant_id):
        cursor = self.db_connection.cursor()
        cursor.execute(f'SELECT stored_charge FROM prosumers where plant_id={plant_id}')
        plant_stored_power = cursor.fetchone()[0]
        self.db_connection.commit()
        return plant_stored_power;

    # Returns wind speed in m/s and temperature in celcius. 
    def get_current_weather(self):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT wind_speed,temperature from weather ORDER BY time_sampled DESC LIMIT 1;')
        wind_speed, temperature = cursor.fetchone()
        self.db_connection.commit() # Update db to sync changes to all calls.
        return (wind_speed, temperature)

    # Insert new log of current weather conditions
    def update_weather(self, new_wind_speed, new_temperature):
        cursor = self.db_connection.cursor()
        cursor.execute(f'INSERT INTO weather(wind_speed, temperature) VALUES({new_wind_speed},{new_temperature})')
        self.db_connection.commit()

    # Returns current price per w/h
    def get_price(self):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT price FROM price_history ORDER BY time_sampled DESC LIMIT 1;')
        price = cursor.fetchone()[0]
        self.db_connection.commit()
        return price

    # Insert log of current w/h price
    def update_price(self, new_price_value):
        cursor = self.db_connection.cursor();
        cursor.execute(f'INSERT INTO price_history(price) VALUES({new_price_value})')
        self.db_connection.commit()

    #Bellow only used by simulator
    # TODO if there is time refactor to give sim its own db_client of a different type than this one.
    # TODO change query when complete.
    def get_updated_plant_storage(self):
        cursor = self.db_connection.cursor()
        #cursor.execute('SELECT plant_id, (current_production-current_consumption+stored_charge) FROM prosumers WHERE active=TRUE;')
        cursor.execute('SELECT plant_id, (current_production-current_consumption+stored_charge) FROM prosumers')
        res = cursor.fetchall()
        self.db_connection.commit()
        return res

    def get_net_storage(self):
        cursor = self.db_connection.cursor()
        #cursor.execute("SELECT SUM(current_production)-SUM(current_consumption)+SUM(stored_charge) FROM prosumers WHERE ACTIVE=TRUE;") 
        cursor.execute("SELECT SUM(current_production)-SUM(current_consumption)+SUM(stored_charge) FROM prosumers")
        res = cursor.fetchone()[0]
        self.db_connection.commit()
        return res
    
    #Returns a list of all valid plant_ids related to token.
    def get_plant_related_token(self,token,plant_ids):
        cursor = self.db_connection.cursor()
        cursor.execute()
        res = cursor.fetchall()
        self.db_connection.commit()
        return res

    def update_plant_storage(self, plant_id, updated_plant_storage):
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET stored_charge={updated_plant_storage} WHERE plant_id={plant_id};')
        self.db_connection.commit()

    def get_active_plants(self):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT plant_id FROM prosumers WHERE active=TRUE')
        res = cursor.fetchall()
        self.db_connection.commit()
        return res
    
    def shutdown_plants(self, plant_ids):
        plant_string ="plant_id="
        prep_stmnt = ""
        for plant_id in plant_ids:
            prep_stmnt+= plant_string+str(plant_id)+' OR '
        prep_stmnt = prep_stmnt.rstrip(' OR ')
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET active=FALSE WHERE {prep_stmnt}')
        self.db_connection.commit()

    def activate_plants(self, plant_ids):
        plant_string ="plant_id="
        prep_stmnt = ""
        for plant_id in plant_ids:
            prep_stmnt+= plant_string+str(plant_id)+' OR '
        prep_stmnt = prep_stmnt.rstrip(' OR ')
        cursor = self.db_connection.cursor()
        cursor.execute(f'UPDATE prosumers SET active=TRUE WHERE {prep_stmnt}')
        self.db_connection.commit()


    



