#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  voip.py
#
#  Copyright 2022 Jens Rapp <tecdroid@tecdroid>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
import hashlib
from datetime import datetime

# TODO: Threading mit Lock implementieren

from voip.sipmessage import *
from voip.udp import UDPClient


class VoIPCall():
    ''' this is the call object
    '''
    def __init__(self, sdpconfig):
        self.sdpconfig = sdpconfig
        self.config = { 'attrib' : {}}
        self.__currentmedia = 'attrib'

        # a function lookup prevents big if-elifififififs
        functions = {
            'm' : self.add_media,
            'v' : self.set_version,
            'a' : self.set_attributes,
            's' : self.set_session,
            'o' : self.set_origin,
            }
        # read every line
        for line in self.sdpconfig.splitlines():
            param, value = line.split('=')
            if param in functions:
                functions[param](value.split(' '))

        # todo open udp socket
        self.client = UDPClient(
            self.config['origin'][-1],
            self.config['audio']['port']
            )
        self.client.open()

    def add_media(self, values):
        ''' add media information
        '''
        mtype = values.pop(0)
        config = {
            'port' : int(values.pop(0)),
            'prot' : values.pop(0),
            'formates' : values,
            }
        self.config[mtype] = config
        # this is for configuring media attributes
        self.__currentmedia = mtype

    def set_version(self, values):
        self.version = int(values[0])

    def set_attributes(self,values):
        # append attributes to
        config = self.config[self.__currentmedia]
        pass

    def set_session(self,values):
        self.config['session'] = ' '.join(values)

    def set_origin(self,values):
        self.config['origin'] = values
        pass

    def send_raw(self, data):
        self.client.write(data)

    def hangup(self):
        self.client.close()


class VoIP(UDPClient):
    ''' this is the voice over ip class
    '''
    def __init__(self,
        server, user, password, port=5060,
        proxy=None, callback=None):
        ''' initialize the voip object
        '''
        super().__init__(server, port, callback)

        self.user = user
        self.password = password
        self.proxy = proxy
        self.call_id = self._gen_callid()

    def connect(self):
        ''' connect to server and authentify
        '''
        self.open()
        # send register request
        register = Register(self.server, self.caller_id, self.call_id)
        resp = self.do_request(register, raw=False)

        if resp.code == 401:
            # generate authentication response
            self.log.debug('Unauthorized as expected')
            register.set_sequence(2)
            register.set_to(resp.get('To'))
            auth = resp.get('WWW-Authenticate')
            method = resp.get('CSeq')[1]
            values = get_values(auth[1])
            register.set(
                'Authorization',
                self.gen_authorization(values,method)
                )

            resp = self.do_request(register, raw=False)
            if resp.code != 200:
                raise(
                    f'authentication got returnval {resp.code} {resp.message}'
                    )

        elif resp.code == 407:
            # generate proxy authentication response
            raise(f'proxy authenticate not yet implemented')

        else:
            raise(f'Unexpected Response Code {resp.code} {resp.message}')

    def call(self, number):
        ''' call a number
        '''
        # call the number first
        invite = Invite(self.server, self.caller_id, self.call_id, number)
        resp = self.do_request(invite, False)
        # response can be one of those
        if resp.code == 401: # authorization
            invite.set_sequence(int (resp.get('CSeq')[0]) +1)
            auth = resp.get('WWW-Authenticate')
            method = resp.get('CSeq')[1]
            values = get_values(auth[1])
            invite.set(
                'Authorization',
                self.gen_authorization(values,method)
                )
            resp = self.do_request(invite, raw=False)

        elif resp.code == 407: #proxy authenticate
            invite.set_sequence(int (resp.get('CSeq')[0]) +1)
            auth = resp.get('Proxy-Authenticate')
            method = resp.get('CSeq')[1]
            values = get_values(auth[1])
            invite.set(
                'Authorization',
                self.gen_authorization(values,method)
                )
            resp = self.do_request(invite, raw=False)
        else:
            raise(f'Unexpected Response Code {resp.code} {resp.message}')

        # wait until it has been received or hung up
        while resp.code in [100,183,401]:
            resp = self.recv(self.BUFFERSIZE, raw=False)

        # if call is received, send ack
        if resp.code == 200:
            ack = Ack(
                self.server,
                self.caller_id,
                self.call_id,
                number,
                int(resp.get('CSeq')[0])
                )
            self.send(ack)
            call = VoIPCall(resp.content)
            return call

        return None

    def hangup(self, call):
        pass

    def _gen_callid(self):
        ''' generate call identifier
        '''
        callid = (self.caller_id + str(datetime.now())).encode('utf8')
        return hashlib.md5(callid).hexdigest()

    def gen_authorization(self, auth, method):
        ''' generate authorization field
        '''
        self.log.debug(f'Generating authentication Digest')
        self.log.debug(f'usthing auth: {auth}')
        self.log.debug(f'using method: {method}')

        # get neccessary information
        realm=auth.get("realm")
        nonce=auth.get("nonce")
        sipuri=f'sip:{self.server};transport=UDP'

        # generate hashes
        ha1str = f'{self.user}:{realm}:{self.password}'
        HA1 = hashlib.md5(ha1str.encode('utf8')).hexdigest()
        ha2str = f'{method}:{self.digest_uri}'
        HA2 = hashlib.md5(ha2str.encode('utf8')).hexdigest()
        rspstr = f'{HA1}:{nonce}:{HA2}'
        response= hashlib.md5(rspstr.encode('utf8')).hexdigest()

        # generate digest string
        s = f'Digest username="{self.user}",realm="{realm}",' + \
            f'nonce="{nonce}",uri="{sipuri}"' + \
            f'response="{response}",algorithm=MD5'
        return s

    @property
    def caller_id(self):
        ''' return caller id
        '''
        return f'"{self.user}" <sip:{self.user}@{self.server}>'

    @property
    def digest_uri(self):
        ''' generate server uri for digest
        '''
        return f'sip:{self.server};transport=UDP'
