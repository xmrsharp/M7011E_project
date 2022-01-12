



import asyncio
import random as r
from db_client import PowerPlantDBClient
#TODO FIX COMMIT AND CATCH FOR CURSOR.EXECUTES.
#TODO Examine if opening and closing db for minor tasks are worth it (allot safer but, if vm cannot handle it switch.)
#TODO Throw exception if credentials are not found.
#TODO Possibly add rain metrics for weather (attribute and update function).
#TODO get wind speeds/temperature from some api like yr or smthng.

class SimGreenMeanMachine:
    def __init__(self, wind_speed=4, temperature=20, price=100):
        with open('DB_CREDENTIALS.txt','r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("sim_user"):
                    line = line.rstrip();
                    self.db_user, _host, self.pw, _database_name = line.split(",");

        self.db_client = PowerPlantDBClient(self.db_user, self.pw)
        #self.db_connection = db.connect('localhost',self.db_user,self.pw);
        
        #WHy is this needed??
        #Updating when creating object to get some base values, need to refactor as this is messy.
        #self.update_weather()
        #self.update_power_price()
        
    def update_power_price(self):
        #TODO: Change to something more realistic, like number of active nodes / some shit, or read assignement as this should be described there. 
        total_stored_charge = self.db_client.get_net_storage()
        current_power_price = self.db_client.get_price()
        if total_stored_charge < 40000:
            new_power_price = current_power_price*(1.5)# inc price.
        elif total_stored_charge < 100000:
            new_power_price = current_power_price*.80 # lower a little
        else:
            new_power_price = current_power_price*.5 # lower price allot as allot of power exists on the market.
        self.db_client.update_price(new_power_price)

    def update_weather(self):
        #TODO Add check if there are no values set in db -> like if we were to deploy (update_weather) and start from scratch.
        current_wind_speed, current_temperature = self.db_client.get_current_weather()
        if r.random() >.95:
            if r.random() > .5:
                current_wind_speed+=1; current_temperature-=1;
            else:
                current_wind_speed-=1; current_temperature+=1;
        self.db_client.update_weather(current_wind_speed,current_temperature)


    def update_plant_storage(self):
        plant_id_storage = self.db_client.get_updated_plant_storage()
        for plant_id, new_storage_balance in plant_id_storage:
            self.db_client.update_plant_storage(plant_id, new_storage_balance)

    # NOTE Only setting of one plant after each iteration.
    def random_blackout(self):
        active_plants = self.db_client.get_active_plants()
        for plant_id in active_plants:
            if r.random() >.97:
                self.db_client.shutdown_plants([plant_id])
                return


    async def run_simulator(self):
        print("simulator main loop starting...")
        while True:
            print(f'sim: db opening con...')
            self.db_client.open_connection()
            print(f'sim: executing events...')
            self.update_weather()
            self.update_plant_storage()
            self.update_power_price()
            self.random_blackout()
            print(f'sim: db closing con...')
            self.db_client.close_connection()
            print(f'going to sleep...')
            await asyncio.sleep(10)



