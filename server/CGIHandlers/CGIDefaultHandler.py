from . import CGIHandler
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIDefaultHandler(CGIHandler.CGIHandler):
    def __init__(self):
        CGIHandler.CGIHandler.__init__(self, None)
    
    def CanExecute(self, file_extension):
        return True
    
    def Execute(self, script, params, data):
        return (HTTPStatus.NOT_IMPLEMENTED, 'No handler defined')