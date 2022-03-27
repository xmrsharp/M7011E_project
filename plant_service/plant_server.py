from sim import SimEngine
from db_client import PowerPlantDBClient
import asyncio
import email
import pprint
import json
import requests
from io import StringIO
from datetime import datetime
import os
from dotenv import load_dotenv
import secrets
import string
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
        # Create json parser for gets.
        self.response_parser = PlantJsonResponseParser()
        # Create ticket machine
        self.ticket_gen = KeyGenerator()

    async def run(self):
        #Bind server to local endpoint.
        print(f'binding to socket...')
        server = await asyncio.start_server(self.handle_request,self.ip,self.port)
        #server.get_loop().create_task(self.sim_engine.run_simulator()) 
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
                if 'plant_id' in query_args:
                    requested_plants = self.db_client.get_plants(query_args['plant_id'])
                elif await self.is_admin(auth_token):
                    requested_plants = self.db_client.admin_get_plants()
                #if self.is_admin(auth_token):
                #    if 'plant_id' in query_args:
                #        #Query plants here, req_plant = self.db_client.get_plants(query_args['plant_id'])
                #    else:
                #        requested_plants = self.db_client.admin_get_plants()
                #elif 'plant_id' in query_args:
                #    requested_plants = self.db_client.get_plants(query_args['plant_id'])
                else:
                    requested_plants = self.db_client.get_plants(authorized_plants)
                return (requested_plants,'plants',200)
            #TODO. ADD THIS REQUEST TO DOCS -> API/PRICE -> RETURN PRICE HISTORY OF
            if end_point.startswith('price'):
                end_point = end_point[5:]
                price_history = self.db_client.get_price_history()
                return (price_history,'price_history',200)


            if end_point.startswith('ticket'):
                end_point = end_point[6:]
                if end_point.startswith('/create'):
                    end_point = end_point[7:]
                    if not await self.is_admin(auth_token):
                        return (None,None,401)
                    new_ticket = self.ticket_gen.gen_key()
                    plant_id = query_args['plant_id'][0]
                    query_res = self.db_client.pair_ticket_plant(new_ticket, plant_id)
                    return ((new_ticket,plant_id), 'new_ticket', 200) 
                expiration_date = self.db_client.get_ticket_expiration(auth_token)
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
        if end_point.startswith('/plant_server/create/'):
            end_point = end_point[21:]
            #Get plant shit.
            created_plant_id = self.db_client.create_plant(query_args['type'], query_args['consumption'], query_args['production'])
            print(f'ALL GOOD SO FAR IN CREATING NEW PLANT.')
            return (created_plant_id,'plant_created',201)
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
                        print(f'LOG: CALL TO ACTIVE STATUS ON  - {e}')
                elif end_point.startswith('off'):
                    end_point = end_point[3:]
                    try:
                        plant_ids = query_args['plant_id'][0] # TODO Fix response parser so arbi number of queries can be executed.
                        self.db_client.shutdown_plant(plant_ids)
                        return ((1,0,plant_ids),'plant_activate',201)
                    except Exception as e :
                        print(f'LOG: CALL TO ACTIVE STATUS OFF - {e}')
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
                # Call to sim_engine
                url = 'http://127.0.0.1/sim/'
                if end_point.startswith('on'):
                    url+='on'
                    print("TODO PREP RESPONSE FOR SIM ON AS SIM SHOULD BE ON SEP SERVER..")
                elif end_point.startswith('off'):
                    url+='off'
                    print("TODO PREP RESPONSE FOR SIM ON AS SIM SHOULD BE ON SEP SERVER..")
                requests.post(url)
                print(f'got response from sim engine')
        return (None,None,400)

    


    async def handle_put_request(self):
        pass
    async def handle_delete_request(self, end_point, auth_token, query_args):
        if not await self.is_admin(auth_token):
            return 401 
        if end_point.startswith('/api/del/plant'):
            end_point = end_point[14:]
            plant_id_delete = int(query_args['plant_id'][0])
            if plant_id_delete < 0:
                return 401
            delete_query = self.db_client.delete_plant(plant_id_delete)
            return 204
        return 400 # Bad request.




    async def generate_ticket_for_user(self, auth_server_key, plant_ids):
        #1. make sure auth_server_key is valid.
        #2. for every plant id, insert the token for being valid to mentioned plant_id
        #3. return token to caller (which in this case is the auth_server (the django apps))
        pass

    # Checks if client has any valid ticket, basically if they have authenticated in the last X hours.
    async def check_ticket_validity(self,ticket):
        ticket_valid, ticket_plants = self.db_client.get_ticket_validity(ticket)
        return ticket_valid, ticket_plants

    async def is_admin(self, auth_token):
        return auth_token==self.auth_secret_key

    async def parse_http_request_info(self,message):
        # pop the first line so we only process headers
        req_details, headers = message.split('\r\n',1)
        req_type, end_point, version = req_details.split(' ', 2)
        # need copy of body as we need content length to know how long the body is.
        body_copy = headers;
        #print(f'HERE1')   
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
        # Remove duplicate query args
        
        # construct a message from the request string
        message = email.message_from_file(StringIO(headers))
        
        # construct a dictionary containing the headers
        headers = dict(message.items())
        
        # Get body sent.
        body = None
        #print(headers)
        if 'Content-Length' in headers and int(headers['Content-Length'])>0:
            print(headers['Content-Length'])
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
        print(f'inc message: {message}')
        try:
            req_type, version, end_point, query_args, headers, body = await self.parse_http_request_info(message)         
        except Exception as badly_formed_request:
            print(f'LOG: Badly formated request')
            await self.bad_request(writer)
            return

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
            if not authorized_access and not await self.is_admin(headers['Authorization']):#headers['Authorization'] != self.auth_secret_key:
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
            if trying_to_access_unauthorized_nodes and not await self.is_admin(headers['Authorization']):
                print("LOG: User is trying to access plants which are not related to ticket")
                await self.unauthorized_request(writer)
                return

        # User has formated according to api documentation and is authorized to access given resources.
                
            
        if API_HEADERS[0] in req_type:
            # GET REQ
            # Perform incoming request. 
            get_server_resp, server_resp_type, status = await self.handle_get_request(end_point, headers['Authorization'],query_args, access_plants_id);
            # Format response of request.
            response_str = self.response_parser.parse_get_response(get_server_resp, server_resp_type, status)
            print(f'RESPONDING GET REQ:\n{response_str}\nTO:[{client_addr}:{_client_port}]\n')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
        elif API_HEADERS[1] in req_type:
            # POST REQ
            post_server_resp, server_resp_type, status = await self.handle_post_request(end_point, headers['Authorization'], query_args, access_plants_id, body)
            response_str = self.response_parser.parse_post_response(post_server_resp, server_resp_type, status)
            print(f'RESPONDING POST REQ:\n{response_str}\nTO:[{client_addr}:{_client_port}]\n')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
        elif API_HEADERS[2] in req_type:
            #PUT REQ
            pass
        elif API_HEADERS[3] in req_type:
            #DELETE REQ
            #Only supporting one del operation currently, which is delete plant, so no need for access_plants_id or body, yey! :D
            status = await self.handle_delete_request(end_point, headers['Authorization'], query_args)
            response_str = self.response_parser.parse_delete_response(status)
            print(f'RESPONDING DEL REQ:\n{response_str}\nTO:[{client_addr}:{_client_port}]\n')
            response_data = response_str.encode("utf-8")
            writer.write(response_data)
            await writer.drain()
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
        self.del_ok = f'HTTP/1.1 204 OK'
        self.bad_request_str = f'HTTP/1.1 400 Bad Request\r\n\r\n\r\n'
        self.unauthorized_request_str = f'HTTP/1.1 401 Unauthorized\r\n\r\n\r\n'
        self.resp_types = {'weather': ['wind_speed','temperature'], 
                          'plants':['plant_id','type_plant','production','consumption','stored','active'],
                          'token_valid':['valid','expiration_date'],
                          'sell_event':['executed','new_storage_amount','tried_to_sell_amount'],
                          'plant_activate':['executed','plant_status','plant_id'],
                          'price_history':['time','price'],
                          'new_ticket':['new_ticket','for_plant_id'],
                          'plant_created':['newly_created_plant']
                          }
    

    def form_body_resp(self,status, headers, body):
        return f'{status}\r\n{headers}\r\n\r\n{body}'
    
    # Used for queries which return a single row of data.
    def prep_body_row(self, keys, tuple_values):
        body = {}
        if not type(tuple_values) is tuple:
            body[keys[0]] = tuple_values
            return json.dumps(body)
        for index,key in enumerate(keys):
            body[key] = tuple_values[index]
        return json.dumps(body)
    
    def prep_body_rows(self, keys, tuple_values):
        body = []
        for tup_value in tuple_values:
            temp_dic = {}
            for index,key in enumerate(keys):
                if type(tup_value[index])==datetime:
                    #TODO, change as this will be sceewed when trying to split and stuff.
                    temp_dic[key] = tup_value[index].strftime("%m/%d/%Y,%H:%M:%S")
                else:
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

    def parse_delete_response(self, status):
        if status == 204:
            headers= self.set_header_length_type(0)
            response = self.form_body_resp(self.del_ok, headers, "")
            return response
        elif status == 401:
            return self.unauthorized_request_str
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
    
class KeyGenerator:
    def gen_key(self, size=16):
        return ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(size))


if __name__ == '__main__':
    server = SimServer()
    asyncio.run(server.run())



