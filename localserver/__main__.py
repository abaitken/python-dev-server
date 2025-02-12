import os
from http.server import HTTPServer
import socketserver
import threading
import CGIHandlerFactory, CustomCGIRequestHandler, Logging

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == '__main__':
    Logging.Level = Logging.LEVEL_INFO
    CGIHandlerFactory.CreateHandlers()
    serverport = os.getenv('SERVERPORT', '8080')
    serveraddr = os.getenv('SERVERADDR', '')
    Logging.Log(Logging.LEVEL_INFO, 'serverport=' + serverport)

    try:
        httpd = ThreadedHTTPServer((serveraddr, int(serverport)),
                                   CustomCGIRequestHandler.CustomCGIRequestHandler)

        print(f"Running server. Use [ctrl]-c to terminate.")

        httpd.serve_forever()

    except KeyboardInterrupt:
        print(f"\nReceived keyboard interrupt. Shutting down server.")
        httpd.socket.close()
