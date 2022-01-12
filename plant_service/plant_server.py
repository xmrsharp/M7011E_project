from sim import SimGreenMeanMachine
from db_client import PowerPlantDBClient
import asyncio
import email
import pprint
from io import StringIO


API_HEADERS = ["GET","POST","PUT","DELETE"]


#TODO add loggs.
#TODO Make db client calls asynchronous, as they're currently blocking.
class SimServer():

    def __init__(self, ip='127.0.0.1', port= '9999'):
        self.ip = ip;
        self.port = port;

        # Get credentials for power_plant db.
        with open('DB_CREDENTIALS.txt','r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("sim_server_user"):
                    line = line.rstrip();
                    self.db_user, _, self.pw, _ = line.split(",")
       
        # Establish connection to power_plant db.
        self.db_client = PowerPlantDBClient(self.db_user, self.pw)
        # Create simulator object.
        self.sim_engine = SimGreenMeanMachine()


    async def run(self):
        #Bind server to local endpoint.
        print(f'binding to socket...')
        server = await asyncio.start_server(self.handle_request,self.ip,self.port)
        server.get_loop().create_task(self.sim_engine.run_simulator()) 
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        print(f'serving on {addrs}...')
        async with server:
            await server.serve_forever()


    async def activate_plant(self, token, node_id):
        #switch state of node_id, to be used with token
        #first check table that token is verified.
        #then update state
        pass
    

    async def sell_power(self, plant_id, amount):
        plant_balance = self.db_client.get_plant_storage(plant_id);
        #if plant_balance+100 < amount:
        # self.db_client.update
        self.db_client.update_plant_storage(plant_id, plant_balance-amount);
        # TODO Will get fucked by all the commits that are happening, but how to update changes within the table otherwise?
        # TODO Look at two or more sequential queries to db.
        #TODO RETURN OK MSG.


    


    
    async def handle_get_request(self):
        pass
    async def handle_post_request(self):
        pass
    async def handle_put_request(self):
        pass
    async def handle_delete_request(self):
        pass
    async def authenticate_user(self,token,plant_ids):
        #token should be existing in db schema.
        
        #plant id should be the related token.
        pass

    async def generate_ticket_for_user(self, auth_server_key, plant_ids):
        #1. make sure auth_server_key is valid.
        #2. for every plant id, insert the token for being valid to mentioned plant_id
        #3. return token to caller (which in this case is the auth_server (the django apps))
        pass


    async def check_ticket_validities(self):
        #To be used in event loop, on a time intervall check that tokens are valid by comparing created/valid through.
        #maybe just delete rows, that way no need to have active alive and will store data of tokens, why even save expired tokens?
        pass

    #credit https://stackoverflow.com/questions/39090366/how-to-parse-raw-http-request-in-python-3 @Corey Goldberg
    async def get_request_headers(self,message):
        req_type_and_http_version, headers = message.split('\r\n', 1)
        message = email.message_from_file(StringIO(headers))
        headers = dict(message.items())
        #Below used for debuging.
        pprint.pprint(headers, width=160)
        return (req_type_and_http_version, headers)

    async def handle_request(self,reader,writer):
        data = await reader.read(500)
        message = data.decode("utf-8")
        req_type, headers = await self.get_request_headers(message)         
        client_addr, _client_port = writer.get_extra_info('peername')

        #TODO FIRST THINGS FIRST, PROCESS AUTH HEADER TO MAKE SURE USER IS VALID.
        #await authenticate_user(#PASS AUTH HEADER HERE)


        if API_HEADERS[0] in req_type:
        #if API_HEADERS[0] in API_METHOD_TYPE:
            print(f'complete message : {message}')
            #how to add { in f string to correctly add to body of json/app msg.
            wind_speed, temperature = self.db_client.get_current_weather()
            price = self.db_client.get_price()
            body = {'used_for_testing':'true','current_wind_speed': wind_speed,'current_temperature':temperature, 'current_price':price} #, 'resource_consumption':sim_response}
            response_str = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{body}'
            #Log bellow in a nicer format.
            print(f'SENDING:{response_str} TO:[{client_addr}:{_client_port}]')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()



        elif API_HEADERS[1] in req_type:
            #POST
            pass
        elif API_HEADERS[2] in req_type:
            #PUT
            pass
        elif API_HEADERS[3] in req_type:
            #DELETE
            pass
        else:
            #Close connection as api method is not valid.
            #Also log missuse from addr.
            pass #pass for now
        with open('log.txt','a') as log_file:
            ##Add timestamp, and make it a read only file with privilages from certain user, that way log file stays intact.
            log_str = f'recieved [{API_METHOD_TYPE}] from [{client_addr}:{_client_port}] with status: {response_str}\n'
            log_file.write(log_str)
        print("close socket connection")
        writer.close()





#For viewing obj attributes, since no dark mode avaliable currently...
def dump(obj):
    for attr in dir(obj):
        if "__" not in attr:
            print("obj.%s = %r" %(attr,getattr(obj,attr)))

if __name__ == '__main__':
    server = SimServer()
    asyncio.run(server.run())



