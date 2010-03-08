# Copyright (C) 2006-2007, Red Hat, Inc.
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

"""User settings/configuration loading.

DEPRECATED. We are using GConf now to store preferences.
"""

import gconf
import os
import logging
from ConfigParser import ConfigParser

from sugar import env
from sugar import util
from sugar.graphics.xocolor import XoColor


_profile = None


class Profile(object):
    """Local user's current options/profile information

    User settings were previously stored in an INI-style
    configuration file. We moved to gconf now. The deprected
    API is kept around to not break activities still using it.

    The profile is also responsible for loading the user's
    public and private ssh keys from disk.

    Attributes:

        pubkey -- public ssh key
        privkey_hash -- SHA has of the child's public key
    """

    def __init__(self, path):
        self._pubkey = None
        self._privkey_hash = None

        self.pubkey = self._load_pubkey()
        self.privkey_hash = self._hash_private_key()

    def is_valid(self):
        client = gconf.client_get_default()
        nick = client.get_string("/desktop/sugar/user/nick")
        color = client.get_string("/desktop/sugar/user/color")

        return nick is not '' and \
               color is not '' and \
               self.pubkey is not None and \
               self.privkey_hash is not None

    def _load_pubkey(self):
        key_path = os.path.join(env.get_profile_path(), 'owner.key.pub')

        if not os.path.exists(key_path):
            return None

        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError:
            logging.exception('Error reading public key')
            return None

        magic = "ssh-dss "
        for l in lines:
            l = l.strip()
            if not l.startswith(magic):
                continue
            return l[len(magic):]
        else:
            logging.error("Error parsing public key.")
            return None

    def _hash_private_key(self):
        key_path = os.path.join(env.get_profile_path(), 'owner.key')

        if not os.path.exists(key_path):
            return None

        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError:
            logging.exception('Error reading private key')
            return None

        key = ""
        begin_found = False
        end_found = False
        for l in lines:
            l = l.strip()
            if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
                begin_found = True
                continue
            if l.startswith("-----END DSA PRIVATE KEY-----"):
                end_found = True
                continue
            key += l
        if not (len(key) and begin_found and end_found):
            logging.error("Error parsing public key.")
            return None

        # hash it
        key_hash = util.sha_data(key)
        return util.printable_hash(key_hash)

    def convert_profile(self):
        cp = ConfigParser()
        path = os.path.join(env.get_profile_path(), 'config')
        cp.read([path])

        client = gconf.client_get_default()

        if cp.has_option('Buddy', 'NickName'):
            name = cp.get('Buddy', 'NickName')
            # decode nickname from ascii-safe chars to unicode
            nick = name.decode("utf-8")
            client.set_string("/desktop/sugar/user/nick", nick)
        if cp.has_option('Buddy', 'Color'):
            color = cp.get('Buddy', 'Color')
            client.set_string("/desktop/sugar/user/color", color)
        if cp.has_option('Jabber', 'Server'):
            server = cp.get('Jabber', 'Server')
            client.set_string("/desktop/sugar/collaboration/jabber_server",
                              server)
        if cp.has_option('Date', 'Timezone'):
            timezone = cp.get('Date', 'Timezone')
            client.set_string("/desktop/sugar/date/timezone", timezone)
        if cp.has_option('Frame', 'HotCorners'):
            delay = float(cp.get('Frame', 'HotCorners'))
            client.set_int("/desktop/sugar/frame/corner_delay", int(delay))
        if cp.has_option('Frame', 'WarmEdges'):
            delay = float(cp.get('Frame', 'WarmEdges'))
            client.set_int("/desktop/sugar/frame/edge_delay", int(delay))
        if cp.has_option('Server', 'Backup1'):
            backup1 = cp.get('Server', 'Backup1')
            client.set_string("/desktop/sugar/backup_url", backup1)
        if cp.has_option('Sound', 'Volume'):
            volume = float(cp.get('Sound', 'Volume'))
            client.set_int("/desktop/sugar/sound/volume", int(volume))
        if cp.has_option('Power', 'AutomaticPM'):
            state = cp.get('Power', 'AutomaticPM')
            if state.lower() == "true":
                client.set_bool("/desktop/sugar/power/automatic", True)
        if cp.has_option('Power', 'ExtremePM'):
            state = cp.get('Power', 'ExtremePM')
            if state.lower() == "true":
                client.set_bool("/desktop/sugar/power/extreme", True)
        if cp.has_option('Shell', 'FavoritesLayout'):
            layout = cp.get('Shell', 'FavoritesLayout')
            client.set_string("/desktop/sugar/desktop/favorites_layout",
                              layout)
        del cp
        try:
            os.unlink(path)
        except OSError:
            logging.error('Error removing old profile.')

    def create_debug_file(self):
        path = os.path.join(os.path.expanduser('~/.sugar'), 'debug')
        fd = open(path, 'w')
        text = '# Uncomment the following lines to turn on many' \
            'sugar debugging\n'\
            '# log files and features\n'\
            '#export LM_DEBUG=net\n' \
            '#export GABBLE_DEBUG=all\n' \
            '#export ' \
            'GABBLE_LOGFILE=$HOME/.sugar/default/logs/telepathy-gabble.log\n' \
            '#export SALUT_DEBUG=all\n' \
            '#export ' \
            'SALUT_LOGFILE=$HOME/.sugar/default/logs/telepathy-salut.log\n' \
            '#export GIBBER_DEBUG=all\n' \
            '#export PRESENCESERVICE_DEBUG=1\n' \
            '#export SUGAR_LOGGER_LEVEL=debug\n\n' \
            '# Uncomment the following line to enable core dumps\n' \
            '#ulimit -c unlimited\n'
        fd.write(text)
        fd.close()


def get_profile():
    global _profile

    if not _profile:
        path = os.path.join(env.get_profile_path(), 'config')
        _profile = Profile(path)

    return _profile


def get_nick_name():
    client = gconf.client_get_default()
    return client.get_string("/desktop/sugar/user/nick")


def get_color():
    client = gconf.client_get_default()
    color = client.get_string("/desktop/sugar/user/color")
    return XoColor(color)


def get_pubkey():
    return get_profile().pubkey
