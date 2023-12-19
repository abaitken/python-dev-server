import subprocess
import os
import Logging
from Utils import which
from . import CGIHandler
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIPHPHandler(CGIHandler.CGIHandler):
    def __init__(self):
        phppath = which('php')
        if phppath is None:
            phppath = 'php'
        
        Logging.Log(Logging.LEVEL_INFO, 'php=' + phppath)
        CGIHandler.CGIHandler.__init__(self, phppath)
    
    def ConstructCommandLine(self, script, params):
        return  [self.interpreter, '-d', 'display_errors=1', '-d', 'error_reporting=4', script, params];
    
    def CanExecute(self, file_extension):
        if file_extension == '.php':
            return True
        return None