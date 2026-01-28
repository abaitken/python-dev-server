import os
from http.server import ThreadingHTTPServer
import threading
import CGIHandlerFactory, CustomCGIRequestHandler, Logging


if __name__ == '__main__':
    Logging.Level = Logging.LEVEL_INFO
    CGIHandlerFactory.CreateHandlers()
    serverport = os.getenv('SERVERPORT', '8080')
    serveraddr = os.getenv('SERVERADDR', '')
    Logging.Log(Logging.LEVEL_INFO, 'serverport=' + serverport)

    try:
        httpd = ThreadingHTTPServer((serveraddr, int(serverport)),
                                   CustomCGIRequestHandler.CustomCGIRequestHandler)

        print(f"Running server. Use [ctrl]-c to terminate.")

        httpd.serve_forever()

    except KeyboardInterrupt:
        print(f"\nReceived keyboard interrupt. Shutting down server.")
        httpd.server_close()
