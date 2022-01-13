from sim import SimGreenMeanMachine
from db_client import PowerPlantDBClient
import asyncio
import email
import pprint
import json
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
        # Create json parser for gets.
        self.response_parser = PlantJsonResponseParser()


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
        # Check to see if the request came from inhouse (:auth header contains inhouse flag and the signed encryption key.)
        # If true -> we want to generate a key for the user and its nodes.
        # By doing it this way this server can reside else where (completing the michro service architecture)
        # The query string if it was inhouse should contain the node_ids of which plants to gain access to.
        # Prep body with the ticket and encrypt via the auth servers public key and sign.
        # auth server will then decrypt with priv key and verify signature.
        # Then simply encrypt with the private key and return the token.
        # HEADER X-Authorization -> req from auth server.
        # 


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


    #stolen from github.
    async def get_request_headers(self,message):
        print(f'THIS IS WHAT IS RETURNED FROM STACK OVERFLOW :\n\n\n ')
        # pop the first line so we only process headers
        req_type_and_http_version, headers = message.split('\r\n', 1)

        # construct a message from the request string
        message = email.message_from_file(StringIO(headers))

        # construct a dictionary containing the headers
        headers = dict(message.items())

        # pretty-print the dictionary of headers
        pprint.pprint(headers, width=160)
        print(f'THIS IS END OF PRETY PRINT \n\n\n')
        return (req_type_and_http_version, headers)

    async def handle_request(self,reader,writer):
        #Reading 500 bytes as waiting for EOF only occurs when for example a curl quits the connection, so read -1 cannot be used.
        data = await reader.read(500)
        #data = await reader.read(-1)    #-1 -> until EOF, EOF ONLY SENT WHEN CURL COMMAND IS CANCELED, WHY?

        message = data.decode("utf-8")
        req_type, headers = await self.get_request_headers(message)         
        
        client_addr, _client_port = writer.get_extra_info('peername')

        #TODO FIRST THINGS FIRST, PROCESS AUTH HEADER TO MAKE SURE USER IS VALID.
        # ! All users should be authorized by auth server before access !
        # Meaning we do not have to process the body what so ever, nice (as that will be done in auth for post)

        if API_HEADERS[0] in req_type:
            #Check for X-Authorization header, as that will signify a msg from authorization service.
            if 'X-Authorization' in headers:
                print(f'GOT A X - AUTHROZIATON HEADER, SHOULD BE SENT BY AUTH SERVER:')
            print(f'entire message \n\n {message} \n\n')    
            #how to add { in f string to correctly add to body of json/app msg.
            #wind_speed, temperature = self.db_client.get_current_weather()
            #price = self.db_client.get_price()
            plants = self.db_client.get_plants([5]);
            response_str = self.response_parser.get_plants_response(200,plants)

            
            print(f'SENDING:{response_str} TO:[{client_addr}:{_client_port}]')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()



        elif API_HEADERS[1] in API_METHOD_TYPE:
            #POST
            pass
        elif API_HEADERS[2] in API_METHOD_TYPE:
            #PUT
            pass
        elif API_HEADERS[3] in API_METHOD_TYPE:
            #DELETE
            pass
        else:
            #Close connection as api method is not valid is not walid.
            #Also log missuse from addr.
            pass

        with open('log.txt','a') as log_file:
            ##Add timestamp, and make it a read only file with privilages from certain user, that way log file stays intact.
            #log_str = f'recieved [{API_METHOD_TYPE}] from [{client_addr}:{_client_port}] with status: {response_str}\n'
            #log_file.write(log_str)
            pass
        print("close socket connection")
        writer.close()

# TODO Rename class to PlantJsonEncoder or something, as current name is not really doing what it is supposed to.
class PlantJsonResponseParser:
    # Keys contains a list of keys (string) , tuple_values a list of tuples which should belong to key in rising order.
    # Need to refactor as implemented methods
    def __init__(self):
        self.bad_request_str = f'HTTP/1.1 400 Bad Request'
        self.good_request_str = f'HTTP/1.1 200 OK'

    def prep_body(self, keys, tuple_values):
        body = []
        for tup_value in tuple_values:
            temp_dic = {}
            for index,key in enumerate(keys):
                temp_dic[key] = tup_value[index]
            body.append(temp_dic)
        return json.dumps(body)

    def parse_weather_response(self, status, weather_status):
        if status == 200:
            body = self.prep_body(['wind_speed','temperature'],weather_status)
            response = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{body}'
            return response;
        return self.bad_request_str
    
    def parse_plants_response(self, status, plant_tuple): 
        if status == 200:
            body = self.prep_body(['plant_id','type_plant','production','consumption','stored','active'],plant_tuple)
            response = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{body}'
            return response
        return self.bad_request_str

    #No authorization for this one, or maybe should be to reduce Botnets from taking over WOOOOOOOO
    def parse_gen_status_response(self, status, gen_status):
        if status == 200:
            body = self.prep_body(['current_price','wind_speed','temperature'],gen_status)
            response = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{body}'
            return response
        return self.bad_request_str



#For viewing obj attributes, since no dark mode avaliable currently...
def dump(obj):
    for attr in dir(obj):
        if "__" not in attr:
            print("obj.%s = %r" %(attr,getattr(obj,attr)))

if __name__ == '__main__':
    server = SimServer()
    asyncio.run(server.run())



