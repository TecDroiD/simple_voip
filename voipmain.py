#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  voipmain.py
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
import logging
import wave
import time

from voip import VoIP, SIPMessage

server = "192.168.178.1"
proxy = ""
user = "auser"
password = "apassword"

def called(call):
    pass

def main(args):

    f = wave.open('announcment.wav', 'rb')
    frames = f.getnframes()
    data = f.readframes(frames)
    f.close()


    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Running in Debug mode.")
    vp = VoIP(server, user, password, proxy=proxy, callback=called)
    vp.connect()

    call = vp.call('01752002091')
    if call is not None:
        time.sleep(1)
        call.send_raw(data)
        vp.hangup(call)
    vp.close()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
