from sim import SimGreenMeanMachine
from db_client import PowerPlantDBClient
import asyncio
import email
import pprint
import json
from io import StringIO
from datetime import datetime
import os
from dotenv import load_dotenv
API_HEADERS = ["GET","POST","PUT","DELETE"]

#TODO add loggs.
#TODO Make db client calls asynchronous, as they're currently blocking.
class SimServer():

    def __init__(self, ip='127.0.0.1', port= '9999'):
        self.ip = ip;
        self.port = port;
        load_dotenv()
        self.db_user = os.getenv('PLANT_SERVER_DB_USER')
        self.pw = os.getenv('PLANT_SERVER_DB_PW')
        self.auth_secret_key = os.getenv('AUTH_SECRET_KEY')
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


    # TODO INSERT CHECK FOR IF ENDPOINTS ARE TO LONG -> SEND BAD REQUEST ERROR.
    # TODO change name of token to ticket.
    # TODO currently key from auth service is sent under authorization header, change that.
    async def handle_get_request(self,end_point, auth_token, query_args, authorized_plants):
        # USER ALREADY AUTHENTICATED HERE.
        if end_point.startswith('/api/'):
            end_point = end_point[5:]
            if end_point.startswith('weather'):
                end_point = end_point[7:]
                wind_speed,temperature = self.db_client.get_current_weather()
                return ((wind_speed, temperature), 'weather',200);

            if end_point.startswith('plants'):
                # Leaving it empty will return all plants related to token.
                end_point = end_point[6:]
                print(f'{auth_token}==?{self.auth_secret_key}')
                print(auth_token==self.auth_secret_key)
                if auth_token == self.auth_secret_key:
                    requested_plants = self.db_client.admin_get_plants()
                elif 'plant_id' in query_args:
                    requested_plants = self.db_client.get_plants(query_args['plant_id'])
                else:
                    requested_plants = self.db_client.get_plants(authorized_plants)
                return (requested_plants,'plants',200)
            
            if end_point.startswith('ticket'):
                end_point = end_point[5:]
                expiration_date = self.db_client.get_ticket_expiration(auth_token)
                #Double check as this will alrdy be authorized. Does not hurt to check again.
                if expiration_date is None:
                    valid=None; status = 401;
                elif expiration_date < datetime.now():
                    valid=False; expiration_date=None; status=200;    
                else:
                    valid=True; expiration_date = expiration_date.strftime("%Y-%m-%d %H:%M:%S"); status=200;
                return ((valid,expiration_date),'token_valid',status)
        return (None,None, 400)  



    #TODO Missing endpoint location of resource in resp call.
    async def handle_post_request(self, end_point, auth_ticket, query_args, authorized_plants, body):
        #print(f"got a post request with: ep{end_point}, ticket: {auth_ticket}\nquery_args: {query_args}\nbody:")
        #try:
        #    print("used for testing, BODY")
        #    for key_value in body.items():
        #        print(f'{key_value}')
        #except Exception as e:
        #    print(f'no dict to be found')
        if end_point.startswith('/api/'):
            end_point = end_point[5:]
            if end_point.startswith('action/'):
                end_point = end_point[7:]
                # Three cases, on, off, and sell.
                if end_point.startswith('on'):
                    end_point = end_point[2:]
                    try:
                        plant_ids = query_args['plant_id'][0] # TODO Fix response parser so arbi number of queries can be executed.
                        self.db_client.activate_plant(plant_ids)
                        return ((1,1,plant_ids),'plant_activate',201)
                    except Exception as e :
                        print(f'exception in call to ON post {e}')
                elif end_point.startswith('off'):
                    end_point = end_point[3:]
                    try:
                        plant_ids = query_args['plant_id'][0] # TODO Fix response parser so arbi number of queries can be executed.
                        self.db_client.shutdown_plant(plant_ids)
                        return ((1,0,plant_ids),'plant_activate',201)
                    except Exception as e :
                        print(f'exception in call to OFF post {e}')
                elif end_point.startswith('sell'):
                    end_point = end_point[4:]
                    try:
                        plant_id = query_args['plant_id'][0]; amount_to_sell = int(query_args['watt_h'])
                        plant_id,_type, _prod, _cons, stored_charge, _active  = self.db_client.get_plants([plant_id])[0]
                        if stored_charge-amount_to_sell < 0:
                            return ((False,stored_charge, amount_to_sell),'sell_event', 403) # result, how to parse, status 
                        # Eligable to sell
                        new_stored_charge = stored_charge-amount_to_sell
                        self.db_client.update_plant_storage(plant_id, new_stored_charge)
                        return ((True, new_stored_charge, amount_to_sell),'sell_event', 201) 
                    except (ValueError,KeyError):
                        print("LOG : missformed query string for specified endpoint.")

        if end_point.startswith('/admin/'):
            end_point = end_point[7:]
            if end_point.startswith('simulator/'):
                end_point = end_point[10:]
                # TODO Add get simulator status.
                if end_point.startswith('on'):
                    self.sim_engine.turn_on()
                    print("TODO PREP RESPONSE FOR SIM ON.")
                elif end_point.startswith('off'):
                    self.sim_engine.turn_off()
                    print("TODO PREP RESPONSE FOR SIM OFF")
        return (None,None,400)



    async def handle_put_request(self):
        pass
    async def handle_delete_request(self):
        pass
    # TODO: Get this operational -> which will cover some other points if we miss them. basically plus.
    # Button in django apps, if logged in, then auth should be the secret key placed.
    # Then generate some random key, and insert with the plant_ids into the db for 6 hours
    # and then return the key to the caller -> where we show it on the browser.

    async def generate_ticket_for_user(self, auth_server_key, plant_ids):
        #1. make sure auth_server_key is valid.
        #2. for every plant id, insert the token for being valid to mentioned plant_id
        #3. return token to caller (which in this case is the auth_server (the django apps))
        pass

    # Checks if client has any valid ticket, basically if they have authenticated in the last X hours.
    async def check_ticket_validity(self,ticket):
        ticket_valid, ticket_plants = self.db_client.get_ticket_validity(ticket)
        return ticket_valid, ticket_plants



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
        print(f'\nINC MSG:\nMsg size: {len(message)} bytes\nMethod: {req_type}\nEndpoint: {end_point}\nheaders: {headers}\nquery str: {query_args}\nbody: {body}\n')
        client_addr, _client_port = writer.get_extra_info('peername')

        # Check authorization header is provided as all incoming requests to this service require authentication. 
        if 'Authorization' not in headers:
            print(f'LOG: User did not specify authorized access token.')
            await self.unauthorized_request(writer)
            return
        else:
            # Ticket provided, now simply fetch all plant ids client has access to.
            authorized_access, access_plants_id = await self.check_ticket_validity(headers['Authorization'])
            if not authorized_access and headers['Authorization'] != self.auth_secret_key:
                print("LOG: User is not authorized to access the resources.")
                await self.unauthorized_request(writer)
                return
        
        # Access_plants_id contains all the authorized plant ids that the ticket holder is eligable to modify.
        # Compare access_plants_id with plant_id from query args, as any request to modify/get those plants should corelate.
        # TODO Revamp ticket schemas, as now a ticket may hold onto different plant ids with different expiration dates.
        # So create new table with ticket/plant id and remove plant_id from tickets.
        # Still works but its an uggly solution.

        if 'plant_id' in query_args:
            #First make query_args into a list if just a simple string, as otherwise '32' will match for '3','2'
            if isinstance(query_args['plant_id'], str):
                query_args['plant_id'] = [query_args['plant_id']]
            trying_to_access_unauthorized_nodes = not all(plant_id in access_plants_id for plant_id in query_args['plant_id'])
            if trying_to_access_unauthorized_nodes:
                print("LOG: User is trying to access plants which are not related to ticket")
                await self.unauthorized_request(writer)
                return

        # User has formated according to api documentation and is authorized to access given resources.
                
            
        if API_HEADERS[0] in req_type:
            # GET REQ
            #Check for X-Authorization header, as that will signify a msg from authorization service.
            if 'X-Authorization' in headers:
                print(f'GOT A X - AUTHROZIATON HEADER, SHOULD BE SENT BY AUTH SERVER:')
            # Perform incoming request. 
            get_server_resp, server_resp_type, status = await self.handle_get_request(end_point, headers['Authorization'],query_args, access_plants_id);
            # Format response of request.
            response_str = self.response_parser.parse_get_response(get_server_resp, server_resp_type, status)
            print(f'RESPONDING:\n{response_str}\nTO:[{client_addr}:{_client_port}]')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
        elif API_HEADERS[1] in req_type:
            # POST REQ
            post_server_resp, server_resp_type, status = await self.handle_post_request(end_point, headers['Authorization'], query_args, access_plants_id, body)
            response_str = self.response_parser.parse_post_response(post_server_resp, server_resp_type, status)
            print(f'RESPONDING:\n{response_str}\nTO:[{client_addr}:{_client_port}]')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
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
        self.post_ok = f'HTTP/1.1 201 Created'
        self.post_forbidden = f'HTTP/1.1 403 Forbidden'
        self.get_ok = f'HTTP/1.1 200 OK'
        self.bad_request_str = f'HTTP/1.1 400 Bad Request\r\n\r\n\r\n'
        self.unauthorized_request_str = f'HTTP/1.1 401 Unauthorized\r\n\r\n\r\n'
        self.resp_types = {'weather': ['wind_speed','temperature'], 
                          'plants':['plant_id','type_plant','production','consumption','stored','active'],
                          'token_valid':['valid','expiration_date'],
                          'sell_event':['executed','new_storage_amount','tried_to_sell_amount'],
                          'plant_activate':['executed','plant_status','plant_id']}
    

    def form_body_resp(self,status, headers, body):
        return f'{status}\r\n{headers}\r\n\r\n{body}'
    
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
    
    
    def set_header_length_type(self, body_length):
        header_length = f'Content-Length: {body_length}\n'
        header_data_type = f'Content-Type: application/json'
        return header_length + header_data_type 

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
            headers = self.set_header_length_type(len(body))
            response = self.form_body_resp(self.get_ok, headers, body)#f'{self.get_ok}Content-Type: application/json\n\n{body}'
            return response
        elif status == 401:
            return self.unauthorized_request_str
        return self.bad_request_str
    
    def parse_post_response(self, resp_data, resp_type, status):
        if status == 201:
            body = self.prep_body_row(self.resp_types[resp_type], resp_data)
            headers = self.set_header_length_type(len(body))
            response_str = self.form_body_resp(self.post_ok, headers, body)
            return response_str
        elif status == 403:
            body = self.prep_body_row(self.resp_types[resp_type], resp_data)
            headers = self.set_header_length_type(len(body))
            response_str = self.form_body_resp(self.post_forbidden, headers, body)
            return response_str
        return self.bad_request_str
    


if __name__ == '__main__':
    server = SimServer()
    asyncio.run(server.run())



