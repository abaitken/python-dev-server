from CGIHandlers import CGIStatefulHandler
from CGIHandlers import CGIPythonHandler
from CGIHandlers import CGIPerlHandler
from CGIHandlers import CGIPHPHandler
from CGIHandlers import CGIDefaultHandler

def CreateHandlers():
    global handlers
    handlers = [ 
            CGIStatefulHandler.CGIStatefulHandler(),
            CGIPythonHandler.CGIPythonHandler(), 
            CGIPerlHandler.CGIPerlHandler(), 
            CGIPHPHandler.CGIPHPHandler(),
            CGIDefaultHandler.CGIDefaultHandler()
        ]

