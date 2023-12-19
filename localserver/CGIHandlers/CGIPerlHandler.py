import subprocess
import os
from Utils import which
import Logging
from . import CGIHandler
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIPerlHandler(CGIHandler.CGIHandler):
    def __init__(self):
        perlpath = which('perl')
        if perlpath is None:
            perlpath = 'perl'
        
        Logging.Log(Logging.LEVEL_INFO, 'perl=' + perlpath)
        CGIHandler.CGIHandler.__init__(self, perlpath)
    
    def CanExecute(self, file_extension):
        if file_extension == '.cgi':
            return True
        if file_extension == '.pl':
            return True
        return None