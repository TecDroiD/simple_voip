import logging
import socket
import select
from threading import Timer, Lock

class UDPClient():
    def __init__(self, server, port, callback = None, buffersize=8196):
        ''' initialize the udp client using `server` and `port`
        additionally, if a callback is given, a thread is started which waits
        until `buffersize` bytes are received.
        callback gets received data as single parameter as in:
        def callback(self, data):
            print(data.encode('utf8')
        '''
        self.log = logging.getLogger(self.__class__.__name__)
        self.server = server
        self.port = port
        self.__callback = callback
        self.buffersize = buffersize
        self.ip = "0.0.0.0"
        self.socket = None

        # if a callback is given run a receive task
        if callback is not None:
            self.t = Timer(1, self.__receive)

    def __receive(self):
        ''' receive function which constantly waits for data and calls
        the callback function
        '''
        while True:
            try:
                data = self.recv(self.buffersize)
                self.__callback(data)
            except:
                pass

    def open(self):
        ''' open udp connection
        '''
        if self.socket is None:
            print(f'Opening connection to {self.server}:{self.port}')
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.ip, self.port))

    def close(self):
        ''' close socket
        '''
        self.log.debug('closing socket')
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def recv(self, buffersize, timeout=30, raw=True):
        ''' receive data
        '''
        ready = select.select([self.socket], [], [], timeout)
        if ready[0]:
            retval = self.socket.recv(buffersize)
            self.log.debug(f'RECEIVED\n====\n{retval.decode()}====\n')
            if raw:
                return retval
            else:
                return SIPMessage.from_text(self.server.encode('utf8'), retval)
        else:
            self.log.error('receive timeout')
            raise TimeoutError("Receiving data from Server timed out")

    def send(self, text):
        ''' send data
        '''
        self.log.debug(f'SENDING\n====\n{str(text)}====\n')
        self.socket.sendto(str(text).encode(),(self.server, self.port))

    def write(self, data):
        ''' send data
        '''
        self.log.debug(f'SENDING {len(data)}bytes\n')
        self.socket.sendto(data,(self.server, self.port))

    def do_request(self, text, raw=True):
        ''' send a text and wait for return value as raw (default) or SIPMessage
        '''
        self.send(text)
        return self.recv(self.buffersize, raw=raw)

