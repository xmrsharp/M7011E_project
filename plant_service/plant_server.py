from sim import SimGreenMeanMachine
from db_client import PowerPlantDBClient
import asyncio
import email
import pprint
import json
from io import StringIO
from datetime import datetime

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


    


    # TODO INSERT CHECK FOR IF ENDPOINTS ARE TO LONG -> SEND BAD REQUEST ERROR.
    async def handle_get_request(self,end_point, auth_token, query_args):
        # USER ALREADY AUTHENTICATED HERE.
        if end_point.startswith('/api/'):
            end_point = end_point[5:]
            if end_point.startswith('weather'):
                end_point = end_point[7:]
                if len(end_point) > 0:
                    #RETURN MISS INFORMATION, i.e. ok.
                    print(f'call exception as endpoint continues with specified : {end_point}, do the same with other endpoints aswell.')
                get_res = self.db_client.get_current_weather()
                return (get_res, 'weather',200);

            if end_point.startswith('plants'):
                # Leaving it empty will return all plants related to token.
                end_point = end_point[6:]
                if 'plant_id' in query_args:
                    requested_plants = self.db_client.get_plants(auth_token, query_args['plant_id'])
                else:
                    requested_plants = self.db_client.get_plants(auth_token, [])
                return (requested_plants,'plants',200)
            
            if end_point.startswith('token'):
                end_point = end_point[5:]
                expiration_date = self.db_client.get_token_expiration(auth_token)
                #Double check as this will alrdy be authorized. Does not hurt to check again.
                if expiration_date is None:
                    valid=None; status = 401;
                elif expiration_date < datetime.now():
                    valid=False; expiration_date=None; status=200;    
                else:
                    valid=True; expiration_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S"); status=200;
                return ((valid,expiration_date),'token_valid',status)
            
            if end_point.startswith('test'):
                get_res = self.db_client.get_plants('TESTING');
                return (get_res,'plants',200)
        
        #Will need authentication for this one.

        # Check to see if the request came from inhouse (:auth header contains inhouse flag and the signed encryption key.)
        # If true -> we want to generate a key for the user and its nodes.
        # By doing it this way this server can reside else where (completing the michro service architecture)
        # The query string if it was inhouse should contain the node_ids of which plants to gain access to.
        # Prep body with the ticket and encrypt via the auth servers public key and sign.
        # auth server will then decrypt with priv key and verify signature.
        # Then simply encrypt with the private key and return the token.
        # HEADER X-Authorization -> req from auth server.

    async def handle_post_request(self):
        pass
    async def handle_put_request(self):
        pass
    async def handle_delete_request(self):
        pass

    async def generate_ticket_for_user(self, auth_server_key, plant_ids):
        #1. make sure auth_server_key is valid.
        #2. for every plant id, insert the token for being valid to mentioned plant_id
        #3. return token to caller (which in this case is the auth_server (the django apps))
        pass

    # Checks if client has any valid ticket, basically if they have authenticated in the last X hours.
    async def check_ticket_validity(self,token):
        ticket_exp_exist = self.db_client.get_token_expiration(token)
        if ticket_exp_exist is None:
            return False
        return True

    #https://stackoverflow.com/questions/54685210/calling-sync-functions-from-async-function For running sync in async function calls.


    async def parse_http_request_info(self,message):
        # pop the first line so we only process headers
        req_details, headers = message.split('\r\n',1)
        req_type, end_point, version = req_details.split(' ', 2)
        # need copy of body as we need content length to know how long the body is.
        body_copy = headers;
        
        query_args = {}
        if '?' in end_point:
            #Query string sent, turn query string into a dict.
            end_point, query_string = end_point.split('?')
            query_vars = query_string.split('&')
            for query_var in query_vars:
                var,value = query_var.split('=')
                if var in query_args:
                    if type(query_args[var]) != list:
                        query_args[var] = [query_args[var],value]
                    else:
                        query_args[var].append(value)

                else:
                    query_args[var]=value

        # construct a message from the request string
        message = email.message_from_file(StringIO(headers))
        
        # construct a dictionary containing the headers
        headers = dict(message.items())
        
        # Get body sent.
        body = None
        if 'Content-Length' in headers:
            body_str = body_copy[len(body_copy)-int(headers['Content-Length']):]
            body = json.loads(body_str)
        return (req_type, version, end_point, query_args, headers, body)

    async def unauthorized_request(self, socket_writer):
        response_str = self.response_parser.parse_unauthorized_response();
        response_data = response_str.encode("utf-8")
        socket_writer.write(response_data)
        await socket_writer.drain()
        socket_writer.close()
        return
    
    async def bad_request(self, socket_writer):
        response_str = self.response_parser.parse_bad_response();
        response_data = response_str.encode("utf-8")
        socket_writer.write(response_data)
        await socket_writer.drain()
        socket_writer.close()
        return

    async def handle_request(self,reader,writer):
        # Reading 500 bytes as waiting for EOF only occurs when for example a curl quits the connection, so read -1 cannot be used.
        data = await reader.read(500)
        message = data.decode("utf-8")
        # Deconstruct inc req.
        try:
            req_type, version, end_point, query_args, headers, body = await self.parse_http_request_info(message)         
        except Exception as badly_formed_request:
            print(f'LOG: Badly formated request')
            await self.bad_request(writer)
            return
        

        #Used for debuging.
        print(f'\nInc msg:\nMsg size: {len(message)} bytes\nMethod: {req_type}\nEndpoint: {end_point}\nheaders: {headers}\nquery str: {query_args}\nbody: {body}\n')
        client_addr, _client_port = writer.get_extra_info('peername')

        # Check authorization header is provided as all incoming requests to this service require authentication. 
        if 'Authorization' not in headers:
            print(f'LOG: User did not specify authorized access token.')
            await self.unauthorized_request(writer)
            return
        else:
            # Ticket provided, now simply check if they have an open ticket that has not expired.
            authorized_access = await self.check_ticket_validity(headers['Authorization'])
            if not authorized_access:
                print("LOG: User is not authorized to access the resources.")
                await self.unauthorized_request(writer)
                return

        # Incoming request is authorized. Can still be unauthorized to get some resources.
        if API_HEADERS[0] in req_type:
            # GET REQ
            #Check for X-Authorization header, as that will signify a msg from authorization service.
            if 'X-Authorization' in headers:
                print(f'GOT A X - AUTHROZIATON HEADER, SHOULD BE SENT BY AUTH SERVER:')
            # Perform incoming request. 
            get_server_resp, server_resp_type, status = await self.handle_get_request(end_point, headers['Authorization'],query_args);
            # Format response of request.
            response_str = self.response_parser.parse_get_response(get_server_resp, server_resp_type, status)
            print(f'\n\nSENDING:\n{response_str} \nTO:[{client_addr}:{_client_port}]')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
        elif API_HEADERS[1] in req_type:
            # POST REQ
            # To include modified/inserted element or not too, that is the question (in response)
            # Only admins are allowed to create new object, or the main auth server.
            # Users are allowed to sell storage though.
            # And buy in the future.
            print("\n\n <------------ GOT A POST REQUEST. TODO ------------->\n\n")
            pass
        elif API_HEADERS[2] in req_type:
            #PUT REQ
            pass
        elif API_HEADERS[3] in req_type:
            #DELETE REQ
            print("\n\n <------------ GOT A DELETE REQUEST. TODO ------------->\n\n")
            pass
        else:
            #Close connection as api method is not valid is not walid.
            print("LOG: request method not supported.")
            await self.bad_request(writer)
            return

        writer.close()


class PlantJsonResponseParser:
    # Keys contains a list of keys (string) , tuple_values a list of tuples which should belong to key in rising order.
    def __init__(self):
        self.bad_request_str = f'HTTP/1.1 400 Bad Request\n\n\n'
        self.unauthorized_request_str = f'HTTP/1.1 401 Unauthorized\n\n\n'
        self.good_request_str = f'HTTP/1.1 200 OK'
        self.resp_types = {'weather': ['wind_speed','temperature'], 
                          'plants':['plant_id','type_plant','production','consumption','stored','active'],
                          'token_valid':['valid','expiration_date']}
    
    # Used for queries which return a single row of data.
    def prep_body_row(self, keys, tuple_values):
        body = {}
        for index,key in enumerate(keys):
            body[key] = tuple_values[index]
        return json.dumps(body)


    def prep_body_rows(self, keys, tuple_values):
        body = []
        for tup_value in tuple_values:
            temp_dic = {}
            for index,key in enumerate(keys):
                temp_dic[key] = tup_value[index]
            body.append(temp_dic)
        return json.dumps(body)
    
    def parse_unauthorized_response(self):
        return self.unauthorized_request_str
    
    def parse_bad_response(self):
        return self.bad_request_str

    def parse_get_response(self, resp_data, resp_type, status):
        if status == 200:
            if isinstance(resp_data[0],tuple):
                # Resp data contains different rows.
                body = self.prep_body_rows(self.resp_types[resp_type], resp_data)
            else:
                body = self.prep_body_row(self.resp_types[resp_type], resp_data)
            response = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{body}'
            return response
        elif status == 401:
            return self.unauthorized_request_str
        return self.bad_request_str


if __name__ == '__main__':
    server = SimServer()
    asyncio.run(server.run())



