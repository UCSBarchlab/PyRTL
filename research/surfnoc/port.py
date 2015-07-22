import pyrtl
from domain import *

class port(object):
    """ This class defines the ports of the router, this will have objects of domain (meaning parametrized)"""

    def __init__(self,portid):
	self.portid=portid

    D0=domain('d0')
    D1=domain('d1')

  
