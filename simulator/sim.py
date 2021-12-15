

"""
    the weather (wind speed specifically)
    electricity consumption
    a modelled current electricity price (based on demand).
"""


#Option, have sim_server read database, this greenmeanmachine simply updating rows in said
#db and then we request the database from the sim_server, that way we're having the
#endpoint only focusing on incoming api requests.


#TODO Add functionality as described in assignement.
#TODO Discuss how to do handle as mentioned above state of consumers/producers.
class GreenMeanMachine:

	def __init__(self):
		self.wind_speed = 0;
		self.current_price = 0;
		self.node_consumption = [];


	def update_wind_speed(self):
		wind_speed = wind_speed/2+2; 

	def update_current_price(self):
		current_price = current_price/2+2;

	def set_current_consumption(self, consumer, current_consumption):
		node_consumption[consumer] = current_consumption;

