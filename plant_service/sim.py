import asyncio
import random as r
from db_client import PowerPlantDBClient
import os
from dotenv import load_dotenv


#TODO Examine if opening and closing db for minor tasks are worth it (allot safer but, if vm cannot handle it switch.)
#TODO Possibly add rain metrics for weather (attribute and update function).
#TODO get wind speeds/temperature from some api like yr or smthng.
class SimEngine:
    def __init__(self, ip ='127.0.0.1', port='9998', wind_speed=4, temperature=20, price=100):
        load_dotenv()
        self.db_user = os.getenv('SIM_ENGINE_DB_USER')
        self.db_pw = os.getenv('SIM_ENGINE_DB_PW')
        self.db_client = PowerPlantDBClient(self.db_user, self.db_pw)
        self.is_active = True;
        self.ip = ip
        self.port= port
        self.valid_response = f'HTTP/1.1 201 Created\r\n\r\n\r\n'
        self.wind_speed=wind_speed
        self.temperature=temperature
        self.price=price

    async def run(self):
        #Bind server to local endpoint.
        print(f'binding to socket...')
        server = await asyncio.start_server(self.sim_server_request, self.ip, self.port)
        server.get_loop().create_task(self.run_simulator())
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        print(f'serving on {addrs}...')
        async with server:
            await server.serve_forever()
    
    
    async def sim_server_request(self,reader,writer):
        data = await reader.read(500)
        message = data.decode("utf-8")
        print(f'RECIEVED {message}...')
        if "on" in message:
            self.active = True
        elif "off" in message:
            self.active = False
        else:
            print(f'LOG: INVALID MESSAGE - {message} ')
        response_str = self.valid_response
        response_data = response_str.encode("utf-8")
        writer.write(response_data)
        await writer.drain()
        writer.close()


    def update_power_price(self):
        total_stored_charge = self.db_client.get_net_storage()
        current_power_price = self.db_client.get_price()
        if total_stored_charge < 40000:
            new_power_price = current_power_price*(1.1)# inc price.
        elif total_stored_charge < 100000:
            new_power_price = current_power_price*.99 # lower a little
        else:
            new_power_price = current_power_price*.95 # lower price allot as allot of power exists on the market.
        if new_power_price > 100:
            new_power_price = 89.41; # To avoid mysql crash
        self.price=new_power_price
        self.db_client.update_price(new_power_price)

    def update_weather(self):
        #TODO Add check if there are no values set in db -> like if we were to deploy (update_weather) and start from scratch.
        current_wind_speed, current_temperature = self.db_client.get_current_weather()
        if r.random() >.5:
            rand = r.random()
            if rand > .5:
                current_wind_speed+=1*rand+1; current_temperature-=1*rand+1;
            else:
                current_wind_speed-=1*rand+1; current_temperature+=1*rand+1;
        if current_wind_speed > 20:
            current_wind_speed=10;
        elif current_wind_speed < 0:
            current_wind_speed=5
        if current_temperature > 40:
            current_temperature=35
        elif current_temperature < -30:
            current_temperature=-25
        self.wind_speed=current_wind_speed
        self.temperature=current_temperature
        self.db_client.update_weather(current_wind_speed,current_temperature)

        
    def update_plant_storage(self):
        plant_id_storage = self.db_client.get_updated_plant_storage()
        for plant_id, new_storage_balance in plant_id_storage:
            self.db_client.update_plant_storage(plant_id, new_storage_balance)

    def update_prod_and_cons(self):
        prosumer_records = self.db_client.engine_get_plants()
        for record in prosumer_records:
            self.upd_prosumer_record(record)    


    def upd_prosumer_record(self, rec):
        #in index:[0]id, [1]type, [2]current_prod, [3]current_cons, [4]active
        #out plantid, new prod, new cons
        #This is really sloppy, doing production cahnges twice. and already have the data right here. but cant see straight, so it goes to the todo pile.
        if rec[4]==0:
            return self.db_client.upd_plant(rec[0], 0, 0)
        #The rest cases are for active plants.
        new_prod = rec[2]
        new_cons = rec[3]
        rand = r.random()
        if rec[1] == 'wind_turbine':
            if self.wind_speed < 5:
                new_prod = new_prod*.95
                new_cons = new_cons*1.1
            else:
                new_prod += 3*rand
            if new_prod > 20:
                new_prod = 5
                new_cons = 5
        elif rec[1] == 'nuclear_reactor':
            if rand > .5:
                new_prod+=3*rand
            else:
                new_prod-=3*rand
            if new_prod > 70 or new_prod < -70:
                new_prod = 45
                new_cons = 40
        elif rec[1] == 'solar_plant':
            if self.temperature < 0:
                new_prod = 0
            elif self.temperature < 20:
                new_prod+= 3*rand
            if new_prod > 10:
                new_prod = 5
                new_cons = 5
        elif rec[1] == 'coal_plant':
            if rand > .3:
                new_prod += 3*rand
            else:
                new_prod -= 2*rand
            if new_prod > 50 or new_prod < -50:
                new_prod = 25
                new_cons = 20
        elif rec[1] == 'house':
            if rand > .4:
                new_prod += 2*rand
            else:
                new_prod -= 3*rand
            if new_prod > 10 or new_prod < -10:
                new_prod = 2
                new_cons = 2
        return self.db_client.upd_plant(rec[0],new_prod, new_cons)
            
    def cleanup_tickets(self):
        self.db_client.remove_expired_tickets()

    # NOTE Only setting of one plant after each iteration.
    def random_blackout(self):
        active_plants = self.db_client.get_active_plants()
        for plant_id in active_plants:
            if r.random() >.97:
                self.db_client.shutdown_plant([plant_id[0]])
                return

    async def run_simulator(self):
        print("simulator engine main loop starting...")
        #TODO: currently only updating weather in a poor way.
        rare_freq = 0
        while True:
            #self.db_client.open_connection()
            print(f'sim: executing events...')
            if rare_freq > 20:
                #Upd weather ever third min.
                self.update_weather()
                self.cleanup_tickets()
                if self.is_active:
                    self.random_blackout()
                rare_freq=0
            self.update_prod_and_cons()
            self.update_plant_storage()
            self.update_power_price()
            #self.db_client.close_connection()
            rare_freq+=1
            print(f'going to sleep...')
            
            await asyncio.sleep(10)


if __name__ == '__main__':
    sim_engine = SimEngine()
    asyncio.run(sim_engine.run())


