import asyncio

API_HEADERS = ["GET","POST","PUT","DELETE"]


#TODO add loggs.
#TODO Cleanup incoming stream processing.
#TODO Prep return body message to HTTP format with headers and status codes and shit.

async def handle_get_request(reader,writer):
	data = await reader.read(100)
		#reader type = asyncio.streams.StreamReader
		#writer type = asyncio.streams.StreamWriter
		#print(f'type of reader: {type(reader)} \n type of writer: {type(writer)}')
	

	print(f'type of data: {type(data)}\n raw data: {data}')
	message = data.decode("utf-8")
	#
	client_addr,_client_port = writer.get_extra_info('peername')
		
	#Recheck for DELETE that all characters are covered in byte indexing.
	API_METHOD_TYPE = message[:6]
	
	if API_HEADERS[0] in API_METHOD_TYPE:
		#GET
		#Process data and resend that shit.
		print(f'recieved: \n{message} from: \n{client_addr}')
		#Prep response, only for testing currently.

		response_str = "200 OK"
		response_data = response_str.encode("utf-8")
		print(f'sending {response_str} to {client_addr}:{_client_port}')
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
	print("close connection")
	writer.close()

#For viewing obj attributes, since no dark mode avaliable currently...
def dump(obj):
	for attr in dir(obj):
		if "__" not in attr:
			print("obj.%s = %r" %(attr,getattr(obj,attr)))


async def test():
	i = 0
	#print("starting loop to see if connections are failed timedout-> send req now")
	while True:
		i+=1
		#print(i)
		if i > 100000000:
			await asyncio.sleep(10)
			i = 0


async def main():
	#Bind server to local endpoint.
	server = await asyncio.start_server(handle_get_request,'127.0.0.1',9999)

	#Only one socket in server.
	#print(f'type of server: {type(server)}')
	#No way around having the 'sim' being yielded too as in the end this server endpoint
	#will remain idle at some point from incoming connections.
	server.get_loop().create_task(test()) #append test to event loop

	addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
	print(f'serving on {addrs}')
	#With used to close server socket before exception -> like cntrl +c
	async with server:
		await server.serve_forever()



asyncio.run(main())