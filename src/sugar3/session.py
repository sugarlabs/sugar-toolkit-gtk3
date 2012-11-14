# Copyright (C) 2008, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
UNSTABLE. Used only internally by jarabe.
"""

import os

from gi.repository import SugarExt


class XSMPClient(SugarExt.ClientXSMP):
    pass


class SessionManager(object):

    def __init__(self):
        address = SugarExt.xsmp_init()
        os.environ['SESSION_MANAGER'] = address
        SugarExt.xsmp_run()

        self.session = SugarExt.Session.create_global()

    def start(self):
        self.session.start()
        self.session.connect('shutdown_completed',
                             self.__shutdown_completed_cb)

    def initiate_shutdown(self):
        self.session.initiate_shutdown()

    def shutdown_completed(self):
        SugarExt.xsmp_shutdown()

    def __shutdown_completed_cb(self, session):
        self.shutdown_completed()
