import subprocess
import os
import Logging
from Utils import which
from . import CGIHandler
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIPythonHandler(CGIHandler.CGIHandler):
    def __init__(self):
        pythonpath = which('python')
        if pythonpath is None:
            pythonpath = which('python3')
        if pythonpath is None:
            pythonpath = 'python'
        
        Logging.Log(Logging.LEVEL_INFO, 'python=' + pythonpath)
        CGIHandler.CGIHandler.__init__(self, pythonpath)
    
    def CanExecute(self, file_extension):
        if file_extension == '.py':
            return True
        return False
