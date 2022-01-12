from sim import SimGreenMeanMachine
from db_client import PowerPlantDBClient
import asyncio



API_HEADERS = ["GET","POST","PUT","DELETE"]


#TODO add loggs.
#TODO Cleanup incoming stream processing.
#TODO Prep return body message to HTTP format with headers and status codes and shit.
#TODO Check string before querying db.
#TODO Rename this server to plants or something similar -> and have plant have a instance of simulator.
#

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
        print(f'creating sim object...')
        #Only one socket in server.
        #print(f'type of server: {type(server)}')
        #No way around having the 'sim' being yielded too as in the end this server endpoint
        #will remain idle at some point from incoming connections.
        server.get_loop().create_task(self.sim_engine.run_simulator()) #append test to event loop
        print(f'appended sim to event loop...')
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        print(f'serving on {addrs}...')
        #With used to close server socket before exception -> like cntrl +c
        async with server:
            await server.serve_forever()

    async def query_fetch_one(self, query):
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        query_res = cursor.fetchone()
        self.db_connection.commit() #commit required to get updated state from db, otherwise the cursor from connection still has an old view of the db.
        return query_res
    
    async def query_fetch_all(self, query):
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        query_res = cursor.fetchall()
        self.db_connection.commit()
        return query_res

    async def activate_plant(self, token, node_id):
        #switch state of node_id, to be used with token
        #first check table that token is verified.
        #then update state
        pass
    
    async def verify_token(self, token, node_id):
        #Verify that incoming token is valid to modify state of node_id.
        pass

    async def sell_power(self, node_id, amount):
        #cursor = self.db_connection.cursor()
        #cursor.execute(f'');
        pass

    def try_decode_msg(self, message):
        call_type, headers = message.split('\r\n', 1)
        print(f'call type: {call_type}\n headers: {headers}')

    async def handle_request(self,reader,writer):
        data = await reader.read(100)
        message = data.decode("utf-8")
        self.try_decode_msg(message);
        client_addr,_client_port = writer.get_extra_info('peername')
        #Recheck for DELETE that all characters are covered in byte indexing.
        API_METHOD_TYPE = message[:6]
        if API_HEADERS[0] in API_METHOD_TYPE:
            #GET
            print(f'RECIEVED:{message}\nFROM:{client_addr}')
            #wind_speed, temperature = await self.query_fetch_one("SELECT wind_speed,temperature FROM weather ORDER BY time_sampled DESC LIMIT 1");
            #price = await self.query_fetch_one("SELECT price FROM price_history ORDER BY time_sampled DESC LIMIT 1")
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



