import pyrtl
from port import *



class router(object):
    """This class defines individual router. It should be instantiated to use in 4*4 torus
    object from each of the class and wire connections are defined here to make it a single router """
    def __init__(self, routerid):
	"""Returns a router with id = routerid"""
	self.routerid=routerid
     
    north=port('north')
    south=port('south')
    west=port('west')
    east=port('east')
