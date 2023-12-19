import Logging
import json
from urllib.parse import parse_qs
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIStatefulHandler:
    #def __init__(self):
    
    def CanExecute(self, file_extension):
        if file_extension == '.state':
            return True
        return False
    
    def Execute(self, script, params, data):
        global state
        
        try:         
            if state is None:
                state = '{}'
        except NameError:
            state = '{}'
        
        #Logging.Log(Logging.LEVEL_INFO, "state: {}".format(state))
        #Logging.Log(Logging.LEVEL_INFO, "data: {}".format(data))
        #Logging.Log(Logging.LEVEL_INFO, "params: {}".format(params))
        
        if data is None:
            return (HTTPStatus.OK, state)
        
        state = data.decode("utf-8")
        return (HTTPStatus.OK, "{}")