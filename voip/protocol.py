import logging
import uuid

class Response():
    ''' this is the response header
    '''
    def __init__(self, text):
        self.log = logging.getLogger(self.__class__.__name__)
        self.text = text
        lines = self.text.splitlines()
        self._get_headline(lines.pop(0))
        self.headers = {}
        self.content = []

        # get header information
        # and finally the content
        position = 0
        for line in lines:
            if len(line) == 0:
                position += 1
            if position == 0:
                self._get_headers(line.decode())
            else:
                self.content.append(line)

    def _get_headline(self, headline):
        data = str(headline.decode())
        self.log.debug(f'Headline: "{data}"')
        self.protocol, code, self.message = data.split(' ', maxsplit=2)
        self.code = int(code)
        self.log.debug(f'Code:{self.code} - {self.message}')

    def _get_headers(self, line):
        if len(line) == 0:
            return False
        head, entry = line.split(': ', maxsplit=1)
        self.log.debug(f'head is {head}')
        entry = entry.replace(', ', ',')
        self.headers[head] = entry.split(' ')
        return True

    def get(self, key):
        return self.headers.get(key)

    def get_values(self, line):
        ''' splits a line into key-value pairs
        '''
        params = {}
        data = line.replace(';', ',')
        data = data.replace('"','')

        for item in data.split(','):
            x = item.split('=', maxsplit=1)
            if len(x) < 2:
                x[1] = None
            params[x[0]] = '='.join(x[1:])
        return params



class Protocol():
    ENDL = '\r\n'
    def __init__(
            self,
            function,
            server,
            port=5060,
            userip='0.0.0.0',
            version = "2.0"
            ):
        self.log = logging.getLogger(self.__class__.__name__)
        self.function = function
        self.server = server
        self.headsip = server
        self.port = port
        self.userip = userip
        self.version = version
        self.headers = {}
        self.content = ''
        self.set_via(f'z9hG4bKt3cDr01d{uuid.uuid4().hex[:25]}')
        self.set_expires()
        self.append('User-Agent', 'T3cPh0n3 0.1')
        self.append('Allow', 'INVITE, ACK, BYE, CANCEL')

    def generate(self, with_content=False):
        ''' create representation string from protocol
        this should finally generate the completeprotocol representation
        '''
        # protocol head generation
        s = f'{self.function} sip:{self.headsip} {self.sipversion}{Protocol.ENDL}'

        # add header data
        for name, entry in self.headers.items():
            e = f'{name}: '
            line = []
            if type(entry) is dict:
                for k, v in entry.items():
                    line.append(f'{str(k)}={str(v)}')
            elif type(entry) in [list, tuple]:
                line = entry
            else:
                line.append(str(entry))
            e += ','.join(line) + Protocol.ENDL
            s += e

        # add content if neccessary
        if with_content is True:
            s += f'Content-Length: {len(self.content)}{Protocol.ENDL}'
            s += str(self.content)

        s += Protocol.ENDL #+ Protocol.ENDL

        return s

    def append(self, key, value):
        ''' append header data
        '''
        self.headers[key] = value

    def get(self, key, value=None):
        ''' get header item
        '''
        return self.headers.get(key, value)

    def expires(self, value):
        ''' set expiring date
        '''
        self.append('Expires', value)

    def __repr__(self):
        ''' create ouptut
        '''
        return self.generate(True)

    def set_sequence(self, number):
        ''' add a sequence entry
        '''
        self.append('CSeq', f'{number} {self.function}')

    def set_from(self, caller):
        ''' add a from entry
        '''
        s =  f'{caller}'
        if 'tag' in self.__dict__:
            s += f';tag={self.tag}'
        self.append('From',s)

    def set_to(self, destination):
        ''' add a receiver entry
        '''
        s =  f'{destination}'
        if 'tag' in self.__dict__:
            s += f';tag={self.tag}'
        self.append('To', s)

    def set_callid(self, call_id):
        ''' add a call id entry
        '''
        self.append('Call-ID', call_id)

    def set_via(self, branch):
        ''' set a via entry
        '''
        x = f'{self.sipversion}/UDP {self.userip}:{self.port};branch={branch};rport'
        self.append('Via', x)

    def set_contact(self, contact):
        ''' set a contact
        '''
        self.append('Contact', contact)

    def set_expires(self, value=120):
        self.append('Expires', value)

    def callee(self, number, server=None):
        cserver = server if server is not None else self.server
        return f'{number}@{cserver}'

    def create_to(self,number, server=None):
        self.set_to(f'<sip:{self.callee(number,server)}>')

    @property
    def sipversion(self):
        return f'SIP/{self.version}'


class Register(Protocol):
    ''' Register-Protocol
    '''
    def __init__(self, server, caller, call_id, cseq=1):
        super().__init__('REGISTER', server)
        self.tag=call_id[:8]
        self.set_from(caller)
        self.set_to(caller)
        self.set_callid(call_id +'@0.0.0.0:5060')
        self.set_sequence(cseq)
        self.set_contact(caller)
        self.set_expires(30)

class Invite(Protocol):
    ''' Invite-Protocol
    '''
    def __init__(self, server, caller, call_id, receiver, cseq=100):
        super().__init__('INVITE', server)
        self.set_from(caller)
        self.set_contact(caller)
        self.set_callid(call_id)
        self.create_to(receiver)
        self.set_sequence(cseq)
        self.headsip=self.callee(receiver)

class Ack(Protocol):
    ''' Acknowledge - sent when OK is sent
    '''
    def __init__(self, server, caller, call_id, receiver, cseq=1):
        super().__init__('ACK', server)
        self.set_from(caller)
        self.create_to(receiver)
        self.set_callid(call_id)
        self.set_sequence(cseq)
