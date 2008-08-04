"""User settings/configuration loading"""
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

import os
import logging
from ConfigParser import ConfigParser

from sugar import env
from sugar import util
from sugar.graphics.xocolor import XoColor

DEFAULT_JABBER_SERVER = 'olpc.collabora.co.uk'
DEFAULT_VOLUME = 81
DEFAULT_TIMEZONE = 'UTC'
DEFAULT_HOT_CORNERS_DELAY = 0.0
DEFAULT_WARM_EDGES_DELAY = 1000.0

RING_LAYOUT = 'ring-layout'
RANDOM_LAYOUT = 'random-layout'
DEFAULT_FAVORITES_LAYOUT = RING_LAYOUT

_profile = None

def _set_key(cp, section, key, value):
    if not cp.has_section(section):
        cp.add_section(section)
    cp.set(section, key, value)

class Profile(object):
    """Local user's current options/profile information
    
    User settings are stored in an INI-style configuration
    file.  This object uses the ConfigParser module to load 
    the settings. (We only very rarely set keys, so we don't
    keep the ConfigParser around between calls.)
    
    The profile is also responsible for loading the user's
    public and private ssh keys from disk.
    
    Attributes:
    
        name -- child's name 
        color -- XoColor for the child's icon
        server -- school server with which the child is 
            associated 
        server_registered -- whether the child has registered 
            with the school server or not
        backup1 -- temporary backup info key for Trial-2
        
        pubkey -- public ssh key
        privkey_hash -- SHA has of the child's public key 
    """
    def __init__(self, path):
        self.nick_name = None
        self.color = None
        self.jabber_server = DEFAULT_JABBER_SERVER
        self.jabber_registered = False
        self.timezone = DEFAULT_TIMEZONE
        self.backup1 = None
        self.sound_volume = DEFAULT_VOLUME
        self.hot_corners_delay = DEFAULT_HOT_CORNERS_DELAY
        self.warm_edges_delay = DEFAULT_WARM_EDGES_DELAY
        self.automatic_pm = False
        self.extreme_pm = False
        self.favorites_layout = DEFAULT_FAVORITES_LAYOUT

        self._pubkey = None
        self._privkey_hash = None
        self._config_path = path

        self._load_config()

    def is_valid(self):
        return self.nick_name is not None and \
               self.color is not None and \
               self.pubkey is not None and \
               self.privkey_hash is not None

    def is_registered(self):
        return self.backup1 is not None

    def save(self):
        cp = ConfigParser()
        cp.read([self._config_path])

        if self.nick_name:
            _set_key(cp, 'Buddy', 'NickName', self.nick_name.encode('utf8'))
        if self.color:
            _set_key(cp, 'Buddy', 'Color', self.color.to_string())
        if self.backup1:
            _set_key(cp, 'Server', 'Backup1', self.backup1)
        if self.jabber_server:
            _set_key(cp, 'Jabber', 'Server', self.jabber_server)

        _set_key(cp, 'Date', 'Timezone', self.timezone)
        
        _set_key(cp, 'Frame', 'HotCorners', self.hot_corners_delay)

        _set_key(cp, 'Frame', 'WarmEdges', self.warm_edges_delay)

        _set_key(cp, 'Jabber', 'Registered', self.jabber_registered)

        _set_key(cp, 'Sound', 'Volume', self.sound_volume)

        _set_key(cp, 'Power', 'AutomaticPM', self.automatic_pm)

        _set_key(cp, 'Power', 'ExtremePM', self.extreme_pm)

        _set_key(cp, 'Shell', 'FavoritesLayout', self.favorites_layout)

        f = open(self._config_path, 'w')
        cp.write(f)
        f.close()

    def _load_config(self):
        cp = ConfigParser()
        cp.read([self._config_path])

        if cp.has_option('Buddy', 'NickName'):
            name = cp.get('Buddy', 'NickName')
            # decode nickname from ascii-safe chars to unicode
            self.nick_name = name.decode("utf-8")
        if cp.has_option('Buddy', 'Color'):
            self.color = XoColor(cp.get('Buddy', 'Color'))
        if cp.has_option('Jabber', 'Server'):
            self.jabber_server = cp.get('Jabber', 'Server')
        if cp.has_option('Jabber', 'Registered'):
            registered = cp.get('Jabber', 'Registered')
            if registered.lower() == "true":
                self.jabber_registered = True
        if cp.has_option('Date', 'Timezone'):
            self.timezone = cp.get('Date', 'Timezone')
        if cp.has_option('Frame', 'HotCorners'):
            self.hot_corners_delay = float(cp.get('Frame', 'HotCorners'))
        if cp.has_option('Frame', 'WarmEdges'):
            self.warm_edges_delay = float(cp.get('Frame', 'WarmEdges'))
        if cp.has_option('Server', 'Backup1'):
            self.backup1 = cp.get('Server', 'Backup1')
        if cp.has_option('Sound', 'Volume'):
            self.sound_volume = float(cp.get('Sound', 'Volume'))
        if cp.has_option('Power', 'AutomaticPM'):
            state = cp.get('Power', 'AutomaticPM')
            if state.lower() == "true":
                self.automatic_pm = True
        if cp.has_option('Power', 'ExtremePM'):
            state = cp.get('Power', 'ExtremePM')
            if state.lower() == "true":
                self.extreme_pm = True
        if cp.has_option('Shell', 'FavoritesLayout'):
            self.favorites_layout = cp.get('Shell', 'FavoritesLayout')

        del cp

    def _load_pubkey(self):
        key_path = os.path.join(env.get_profile_path(), 'owner.key.pub')
        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError, e:
            logging.error("Error reading public key: %s" % e)
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

    def _get_pubkey(self):
        # load on-demand.
        if not self._pubkey:
            self._pubkey = self._load_pubkey()
        return self._pubkey

    def _hash_private_key(self):
        key_path = os.path.join(env.get_profile_path(), 'owner.key')
        try:
            f = open(key_path, "r")
            lines = f.readlines()
            f.close()
        except IOError, e:
            logging.error("Error reading private key: %s" % e)
            return None

        key = ""
        for l in lines:
            l = l.strip()
            if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
                continue
            if l.startswith("-----END DSA PRIVATE KEY-----"):
                continue
            key += l
        if not len(key):
            logging.error("Error parsing public key.")
            return None

        # hash it
        key_hash = util._sha_data(key)
        return util.printable_hash(key_hash)

    def _get_privkey_hash(self):
        # load on-demand.
        if not self._privkey_hash:
            self._privkey_hash = self._hash_private_key()
        return self._privkey_hash

    privkey_hash = property(_get_privkey_hash)
    pubkey = property(_get_pubkey)

def get_profile():
    global _profile

    if not _profile:
        path = os.path.join(env.get_profile_path(), 'config')
        _profile = Profile(path)

    return _profile

# Convenience methods for frequently used properties

def get_nick_name():
    return get_profile().nick_name

def get_color():
    return get_profile().color

def get_pubkey():
    return get_profile().pubkey
