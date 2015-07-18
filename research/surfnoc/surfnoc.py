import pyrtl



class port(object):
    """ This is port class, which will be used to create N S E W ports of the router. This contains buffer."""

    def __init__(self, name):
        """This is used to instantiate each port of the router"""
        self.name=name

    def buf_fer():
        """Buffer"""



class surf_noc(object):
    """This class defines individual router. It should be instantiated to use in 4*4 torus
    Router as 1.Buffer 2.Route Computation Unit(RC) 3.Virtual Channel Allocator(VC) 4.Switch Allocator (SA) 5. Crossbar

    """
    def __init__(self, routerid):
	"""Returns a router with id = routerid"""
	self.routerid=routerid
     
    north_port=port('north')
    south_port=port('south')
    east_port=port('east')
    west_port=port('west')
	

    def route_computer():
	"""Route Computer"""

    def vc_allocator():
	"""Virtual Channel Allocator"""


    def sw_allocator():
	"""Switch Allocator"""


    def crossbar():
	"""Crossbar"""


