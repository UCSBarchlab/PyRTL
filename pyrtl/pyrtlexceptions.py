""" The set of error types thrown by PyRTL. """

# -----------------------------------------------------------------
#   ___  __   __   __   __  ___      __   ___  __
#  |__  |__) |__) /  \ |__)  |  \ / |__) |__  /__`
#  |___ |  \ |  \ \__/ |  \  |   |  |    |___ .__/
#


class PyrtlError(Exception):
    """ Raised on any user-facing error in this module """
    pass


class PyrtlInternalError(Exception):
    """ Raised on any PyRTL internal failure """
    pass
