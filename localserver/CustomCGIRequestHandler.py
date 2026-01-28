import copy
import os
import re
from http.server import SimpleHTTPRequestHandler
from http import HTTPStatus #https://docs.python.org/3/library/http.html
import CGIHandlerFactory
import urllib.parse
import select

import datetime
import email.utils
import html
import http.client
import io
import itertools
import mimetypes
import posixpath
import shutil
import socket # For gethostbyaddr()
import socketserver
import sys
import time
import traceback

from http import HTTPStatus
import Logging

def ltrim(value, c):
    s = value
    if s is not None and s.startswith(c):
        s = s[len(c):]
    
    return s

def GetHeader(value, header):
    result = re.search(r'^' + re.escape(header) + r':\s*(.+?)\r?\n', value, re.MULTILINE | re.IGNORECASE)
    if result is None:
        return None
    
    return result.group(1)

def RemoveHeader(value, header):
    result = re.sub(r'^' + re.escape(header) + r':\s*(.+?)\r?\n', '', value, 0, re.MULTILINE | re.IGNORECASE)    
    return result

def _url_collapse_path(path):
    """
    Given a URL path, remove extra '/'s and '.' path elements and collapse
    any '..' references and returns a collapsed path.

    Implements something akin to RFC-2396 5.2 step 6 to parse relative paths.
    The utility of this function is limited to is_cgi method and helps
    preventing some security attacks.

    Returns: The reconstituted URL, which will always start with a '/'.

    Raises: IndexError if too many '..' occur within the path.

    """
    # Query component should not be involved.
    path, _, query = path.partition('?')
    path = urllib.parse.unquote(path)

    # Similar to os.path.split(os.path.normpath(path)) but specific to URL
    # path semantics rather than local operating system semantics.
    path_parts = path.split('/')
    head_parts = []
    for part in path_parts[:-1]:
        if part == '..':
            head_parts.pop() # IndexError if more '..' than prior parts
        elif part and part != '.':
            head_parts.append( part )
    if path_parts:
        tail_part = path_parts.pop()
        if tail_part:
            if tail_part == '..':
                head_parts.pop()
                tail_part = ''
            elif tail_part == '.':
                tail_part = ''
    else:
        tail_part = ''

    if query:
        tail_part = '?'.join((tail_part, query))

    splitpath = ('/' + '/'.join(head_parts), tail_part)
    collapsed_path = "/".join(splitpath)

    return collapsed_path

BYTE_RANGE_RE = re.compile(r'bytes=(\d+)-(\d+)?$')
def parse_byte_range(byte_range):
    """Returns the two numbers in 'bytes=123-456' or throws ValueError.

    The last number or both numbers may be None.
    """
    if byte_range.strip() == '':
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise ValueError('Invalid byte range %s' % byte_range)

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise ValueError('Invalid byte range %s' % byte_range)
    return first, last

def copy_byte_range(infile, outfile, start=None, stop=None, bufsize=16*1024):
    """Like shutil.copyfileobj, but only copy a range of the streams.

    Both start and stop are inclusive.
    """
    if start is not None: infile.seek(start)
    while 1:
        to_read = min(bufsize, stop + 1 - infile.tell() if stop else bufsize)
        buf = infile.read(to_read)
        if not buf:
            break
        outfile.write(buf)

class CustomCGIRequestHandler(SimpleHTTPRequestHandler):

    cgi_directories = ['/cgi-bin', '/htbin']
    # Make rfile unbuffered -- we need to read one line and then pass
    # the rest to a subprocess, so we can't use buffered input.
    rbufsize = 0
    
    def __init__(self,req,client_addr,server):
        SimpleHTTPRequestHandler.__init__(self,req,client_addr,server)
        #super(req, client_addr, server)
    
    def serverSideScriptInterpreterSelector(self, script):
        file_name, file_extension = os.path.splitext(script)    
        for item in CGIHandlerFactory.handlers:
            if item.CanExecute(file_extension):
                return item
                
        return None
    
    def parse_path(self, path):
        parts = path.split('?', 2)
        params = ''
        if len(parts) == 2:
            params = parts[1]
        
        parts = parts[0].split('#', 2)
        path = parts[0]
        
        return (path, params)
        
    def is_cgi(self):
        """Test whether self.path corresponds to a CGI script.

        Returns True and updates the cgi_info attribute to the tuple
        (dir, rest) if self.path requires running a CGI script.
        Returns False otherwise.

        If any exception is raised, the caller should assume that
        self.path was rejected as invalid and act accordingly.

        The default implementation tests whether the normalized url
        path begins with one of the strings in self.cgi_directories
        (and the next character is a '/' or the end of the string).

        """
        self.cgi_info = None
        collapsed_path = _url_collapse_path(self.path)
        dir_sep = collapsed_path.find('/', 1)
        while dir_sep > 0 and not collapsed_path[:dir_sep] in self.cgi_directories:
            dir_sep = collapsed_path.find('/', dir_sep+1)
        if dir_sep > 0:
            head, tail = collapsed_path[:dir_sep], collapsed_path[dir_sep+1:]
            self.cgi_info = head, tail
            return True
        return False
    
    def prepareEnvironment(self):
        dir, rest = self.cgi_info
        path = dir + '/' + rest
        i = path.find('/', len(dir)+1)
        while i >= 0:
            nextdir = path[:i]
            nextrest = path[i+1:]

            scriptdir = self.translate_path(nextdir)
            if os.path.isdir(scriptdir):
                dir, rest = nextdir, nextrest
                i = path.find('/', len(dir)+1)
            else:
                break

        # find an explicit query string, if present.
        rest, _, query = rest.partition('?')

        # dissect the part after the directory name into a script name &
        # a possible additional path, to be stored in PATH_INFO.
        i = rest.find('/')
        if i >= 0:
            script, rest = rest[:i], rest[i:]
        else:
            script, rest = rest, ''

        scriptname = dir + '/' + script
        scriptfile = self.translate_path(scriptname)
        # Reference: http://hoohoo.ncsa.uiuc.edu/cgi/env.html
        # XXX Much of the following could be prepared ahead of time!
        env = copy.deepcopy(os.environ)
        env['SERVER_SOFTWARE'] = self.version_string()
        env['SERVER_NAME'] = self.server.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PROTOCOL'] = self.protocol_version
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_METHOD'] = self.command
        uqrest = urllib.parse.unquote(rest)
        env['PATH_INFO'] = uqrest
        env['PATH_TRANSLATED'] = self.translate_path(uqrest)
        env['SCRIPT_NAME'] = scriptname
        env['QUERY_STRING'] = query
        env['REQUEST_URI'] = 'http://' + self.server.server_name + ':' + str(self.server.server_port) + scriptname + '?' + query
        env['REMOTE_ADDR'] = self.client_address[0]
        authorization = self.headers.get("authorization")
        if authorization:
            authorization = authorization.split()
            if len(authorization) == 2:
                import base64, binascii
                env['AUTH_TYPE'] = authorization[0]
                if authorization[0].lower() == "basic":
                    try:
                        authorization = authorization[1].encode('ascii')
                        authorization = base64.decodebytes(authorization).\
                                        decode('ascii')
                    except (binascii.Error, UnicodeError):
                        pass
                    else:
                        authorization = authorization.split(':')
                        if len(authorization) == 2:
                            env['REMOTE_USER'] = authorization[0]
        # XXX REMOTE_IDENT
        if self.headers.get('content-type') is None:
            env['CONTENT_TYPE'] = self.headers.get_content_type()
        else:
            env['CONTENT_TYPE'] = self.headers['content-type']
        length = self.headers.get('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        referer = self.headers.get('referer')
        if referer:
            env['HTTP_REFERER'] = referer
        accept = self.headers.get_all('accept', ())
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.get('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        co = filter(None, self.headers.get_all('cookie', []))
        cookie_str = ', '.join(co)
        if cookie_str:
            env['HTTP_COOKIE'] = cookie_str
        # XXX Other HTTP_* headers
        # Since we're setting the env in the parent, provide empty
        # values to override previously set values
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
                  'HTTP_USER_AGENT', 'HTTP_COOKIE', 'HTTP_REFERER'):
            env.setdefault(k, "")
    
    def run_cgi(self, script, params):
    
        try:
            self.prepareEnvironment()        
        except Exception as e:
            Logging.Log(Logging.LEVEL_ERROR, f"Exception: {type(e)}")
            Logging.Log(Logging.LEVEL_ERROR, f"Detail: {str(e)}")
            tb = traceback.format_exc()
            Logging.Log(Logging.LEVEL_ERROR, tb)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, 'Internal server error')
            return None
        
        length = self.headers.get('content-length')
        try:
            nbytes = int(length)
        except (TypeError, ValueError):
            nbytes = 0
        if self.command.lower() == "post" and nbytes > 0:
            data = self.rfile.read(nbytes)
        else:
            data = None
        # throw away additional data [see bug #427345]
        while select.select([self.rfile._sock], [], [], 0)[0]:
            if not self.rfile._sock.recv(1):
                break
            
        (exitcode, output) = self.serverSideScriptInterpreterSelector(script).Execute(script, params, data)
        
        status = GetHeader(output, "Status")
        if status is not None:
            self.send_response(int(status[:3]))
            output = RemoveHeader(output, "Status")
        else:
            self.send_response(HTTPStatus.OK)
        
        contentType = GetHeader(output, "Content-Type")
        if contentType is not None:
            self.send_header("Content-type", contentType)
            output = RemoveHeader(output, "Content-Type")
        else:
            self.send_header("Content-Type", "text/html")
        
        expires = GetHeader(output, "Expires")
        if expires is not None:
            self.send_header("Expires", expires)
            output = RemoveHeader(output, "Expires")
        
        date = GetHeader(output, "Date")
        if date is not None:
            self.send_header("Date", date)
            output = RemoveHeader(output, "Date")
        
        output = RemoveHeader(output, "Content-length")
        output = output.lstrip()
        
        self.send_header("Content-length", len(output))
        self.end_headers()
        self.wfile.write(bytes(output, "utf-8"))

    def end_headers(self):
        if not self.command.lower() == "post" and self.cgi_info == None:
            self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        return super().end_headers()
    
    def do_POST(self):
        # If not running a cgi script
        if not self.is_cgi():
            output = 'POST available to CGI only'
            self.send_response(HTTPStatus.FORBIDDEN)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-length", len(output))
            self.end_headers()
            self.wfile.write(bytes(output, 'utf-8'))
            return
            
        # Perform CGI request
        (scriptPath, params) = self.parse_path(self.path)        
        script = self.translate_path(scriptPath)
        self.run_cgi(script, params)
        
    def _do_GET_Range(self):
        try:
            self.range = parse_byte_range(self.headers['Range'])
        except ValueError as e:
            self.send_error(HTTPStatus.BAD_REQUEST, 'Invalid byte range')
            
        first, last = self.range
        
        # Mirroring SimpleHTTPServer.py here
        path = self.translate_path(self.path)
        f = None
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except IOError:
            self.send_error(HTTPStatus.NOT_FOUND, 'File not found')
            return None

        fs = os.fstat(f.fileno())
        file_len = fs[6]
        if first >= file_len:
            self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, 'Requested Range Not Satisfiable')
            return None

        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header('Content-type', ctype)

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        self.send_header('Content-Range',
                         'bytes %s-%s/%s' % (first, last, file_len))
        self.send_header('Content-Length', str(response_length))
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.end_headers()
        
        # SimpleHTTPRequestHandler uses shutil.copyfileobj, which doesn't let
        # you stop the copying before the end of the file.
        start, stop = self.range  # set in send_head()
        copy_byte_range(f, self.wfile, start, stop)
        
        f.close()
        
        
    def do_GET(self):            
        # If not running a cgi script, run a regular request
        if not self.is_cgi():
            self.range = None
            if 'Range' in self.headers:
                self._do_GET_Range()
                return
            
            super().do_GET()
            return

        # Perform CGI request
        (scriptPath, params) = self.parse_path(self.path)        
        script = self.translate_path(scriptPath)
        self.run_cgi(script, params)
