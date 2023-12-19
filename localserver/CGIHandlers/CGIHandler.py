import subprocess
import os
import Logging
from http import HTTPStatus #https://docs.python.org/3/library/http.html

class CGIHandler:
    def __init__(self, interpreter):
        self.interpreter = interpreter
    
    def CanExecute(self, file_extension):
        raise NotImplementedError()
    
    def ConstructCommandLine(self, script, params):
        return  [self.interpreter, script, params];
        
    def Execute(self, script, params, data):
        if not os.path.isfile(script):
            return (HTTPStatus.NOT_FOUND, 'Resource not found')
        
        cmdline = self.ConstructCommandLine(script, params)
        Logging.Log(Logging.LEVEL_INFO, "command: {}".format(subprocess.list2cmdline(cmdline)))
        proc = subprocess.run(cmdline, input=data, capture_output=True)
        
        if proc.returncode != 0:
            output = proc.stderr.decode("utf-8") + proc.stdout.decode("utf-8")
            return (HTTPStatus.INTERNAL_SERVER_ERROR, output)
        
        Logging.Log(Logging.LEVEL_WARN, proc.stderr.decode("utf-8"))
        return (HTTPStatus.OK, proc.stdout.decode("utf-8"))
