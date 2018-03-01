# Copyright (C) 2006-2007 Red Hat, Inc.
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

'''
Provides a class for storing activity metadata such as activity id's,
journal object id's,
'''


class ActivityHandle(object):
    '''
    Data structure storing simple activity metadata

    Args:
        activity_id (string): unique id for the activity to be
        created

        object_id (string): identity of the journal object
        associated with the activity.

        When you resume an activity from the journal
        the object_id will be passed in. It is optional
        since new activities does not have an
        associated object.

        uri (string): URI associated with the activity. Used when
        opening an external file or resource in the
        activity, rather than a journal object
        (downloads stored on the file system for
        example or web pages)

        invited (bool): True if the activity is being
        launched for handling an invite from the network
    '''

    def __init__(self, activity_id=None, object_id=None, uri=None,
                 invited=False):
        self.activity_id = activity_id
        self.object_id = object_id
        self.uri = uri
        self.invited = invited

    def get_dict(self):
        '''Returns activity settings as a dictionary in format
            {activity_id:XXXX, object_id:XXXX, uri:XXXX, invited:BOOL}'''
        result = {'activity_id': self.activity_id, 'invited': self.invited}
        if self.object_id:
            result['object_id'] = self.object_id
        if self.uri:
            result['uri'] = self.uri

        return result


def create_from_dict(handle_dict):
    '''Returns an activity handle from a dictionary of parameters'''
    result = ActivityHandle(handle_dict['activity_id'],
                            object_id=handle_dict.get('object_id'),
                            uri=handle_dict.get('uri'),
                            invited=handle_dict.get('invited'))
    return result
