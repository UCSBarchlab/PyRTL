import pyrtl
from vchannel import *

class domain(object):
    """ This class defines the domain. Object for virtual class can be created, this can be used to parametrize no of virtual channels"""

    def __init__(self,domainid):
	self.domainid=domainid
    VC0=vchannel('vc0')
    VC1=vchannel('vc1')

    
