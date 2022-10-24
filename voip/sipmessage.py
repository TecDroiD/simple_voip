import logging
import uuid

def get_values(line):
    ''' splits a text into key-value pairs
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

class SIPMessage():
    ''' this is a sip message which is basically used to communicate between
    server and client
    '''
    ENDL = '\r\n'
    SIPVERSION = '2.0'

    @staticmethod
    def from_text(server, text):
        data = text.decode()
        # since the first differs from the others, split it away
        typestr, message = data.split(SIPMessage.ENDL, maxsplit=1)
        # extract important information
        sipversion, codestr, function = typestr.split(' ', maxsplit=2)

        # create message
        msg = SIPMessage('', server, code=int(codestr))
        msg.text = data

        # split headers and content and add them to the message
        headers, content = message.split(
                f'{SIPMessage.ENDL}{SIPMessage.ENDL}',
                maxsplit=1
                )
        msg.parse_headers(headers)
        msg.set_content(content.strip())

        return msg

    def __init__(self, function, server, port=5060, code=None, mesg=None):
        ''' initialize it all
        '''
        self.log = logging.getLogger(self.__class__.__name__)
        self.function = function
        self.server = server
        self.code = code
        self.message = mesg
        self.is_response = True if self.code is not None else False
        self.port = port
        self.headers = {}
        self.content = ''

    def __repr__(self):
        ''' create string representation
        '''
        return self.generate(True)

    def set_content(self, content):
        ''' set the message content
        '''
        self.content = content

    def parse_headers(self, headers):
        ''' set header data
        '''
        lines = headers.splitlines()
        for line in lines:
            self.get_header(line)

    def get_header(self, line):
        ''' parses a single header line
        '''
        if len(line) == 0:
            return False
        head, entry = line.split(': ', maxsplit=1)
        self.log.debug(f'head is {head}')
        entry = entry.replace(', ', ',')
        self.headers[head] = entry.split(' ')
        return True

    def generate(self, with_content=True):
        s = ''
        # first line is different - depending on what the message is
        if self.is_response:
            s += f'{self.sipversion} {self.code} {self.message}{self.ENDL}'
        else:
            s = f'{self.function} sip:{self.headsip} {self.sipversion}{self.ENDL}'

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
            e += ','.join(line) + self.ENDL
            s += e

        # add content if neccessary
        if with_content is True:
            s += f'Content-Length: {len(self.content)}{self.ENDL}'
            s += str(self.content)

        s += self.ENDL

        return s

    def get(self, key, value=None):
        ''' get value by key
        '''
        return self.headers.get(key, value)

    def set(self, key, value):
        ''' set a header value
        '''
        self.headers[key] = value

    @property
    def sipversion(self):
        ''' generate a sip version entry
        '''
        return f'SIP/{self.SIPVERSION}'

    @property
    def sdpcontent(self):
        if not '_sdpcontent' in self.__dict__:
            self._sdpcontent = {}
            lines = self.content.splitlines()


        return self._sdpcontent


class SIPRequest(SIPMessage):
    ''' this is the base request
    '''
    def __init__(
            self,
            function,
            server,
            port=5060,
            userip='0.0.0.0',
            ):
        super().__init__(function, server, port=port)
        self.log = logging.getLogger(self.__class__.__name__)

        self.headsip = server
        self.userip = userip
        self.set_via(f'z9hG4bKt3cDr01d{uuid.uuid4().hex[:25]}')
        self.set_expires()
        self.set('User-Agent', 'T3cPh0n3 0.1')
        self.set('Allow', 'INVITE, ACK, BYE, CANCEL')

    def set_sequence(self, number):
        ''' add a sequence entry
        '''
        self.set('CSeq', f'{number} {self.function}')

    def set_from(self, caller):
        ''' add a from entry
        '''
        s =  f'{caller}'
        if 'tag' in self.__dict__:
            s += f';tag={self.tag}'
        self.set('From',s)

    def set_to(self, destination):
        ''' add a receiver entry
        '''
        if type(destination) == list:
            self.set('To', ' '.join(destination))
            return
        s =  f'{destination}'
        if 'tag' in self.__dict__:
            s += f';tag={self.tag}'
        self.set('To', s)

    def set_callid(self, call_id):
        ''' add a call id entry
        '''
        self.set('Call-ID', call_id)

    def set_via(self, branch):
        ''' set a via entry
        '''
        x = f'{self.sipversion}/UDP {self.userip}:{self.port};branch={branch};rport'
        self.set('Via', x)

    def set_contact(self, contact):
        ''' set a contact
        '''
        self.set('Contact', contact)

    def set_expires(self, value=30):
        ''' set expire time for the message
        '''
        self.set('Expires', value)

    def callee(self, number, server=None):
        cserver = server if server is not None else self.server
        return f'{number}@{cserver}'

    def create_to(self,number, server=None):
        self.set_to(f'<sip:{self.callee(number,server)}>')


class Register(SIPRequest):
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


class Invite(SIPRequest):
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


class Ack(SIPRequest):
    ''' Acknowledge - sent when OK is sent
    '''
    def __init__(self, server, caller, call_id, receiver, cseq=1):
        super().__init__('ACK', server)
        self.set_from(caller)
        self.create_to(receiver)
        self.set_callid(call_id)
        self.set_sequence(cseq)
if __name__ == '__main__':
    req = SIPRequest('REGISTER', 'fritz.box')
    print(req)
