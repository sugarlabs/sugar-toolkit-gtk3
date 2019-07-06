# Copyright (C) 2010, OLPC
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
Validation and normalization of bundle versions.

Instances of :class:`NormalizedVersion` can be directly compared;

    >>> from sugar3.bundle.bundleversion import NormalizedVersion
    >>> a = NormalizedVersion('157.3')
    >>> b = NormalizedVersion('201.2')
    >>> a > b
    False
    >>> b > a
    True

Invalid versions will raise :exc:`InvalidVersionError`.

Valid versions are `1`, `1.2`, `1.2.3`, `1.2.3-peru`, and
`1.2.3~dfsg`.

Invalid versions are:
    * `1.2peru` (because the suffix must be preceded with a dash or tilde),
    * `1.2.` (because a version can't end with a period), or
    * `1.02.5` (because a version can't have a leading zero).

Based on the implementation of :pep:`386`, but adapted to our
numeration schema.

Attributes:
    VERSION_RE (RegexObject): regular expression for versions,\
    deprecated, as it is insufficient by itself.
"""

import re


VERSION_RE = re.compile(r'''
    ^
    (?P<version>\d+)               # minimum 'N'
    (?P<extraversion>(?:\.\d+)*)   # any number of extra '.N' segments
    (?:
    (?P<local>[\-\~].[a-zA-Z]*)    # ignore any string in the comparison
    )?
    $''', re.VERBOSE)


class InvalidVersionError(Exception):
    """
    A version cannot be normalized, because:
        * the object is not a string,
        * the string does not match the regular expression, or
        * the string has a leading zero in a version part.
    """
    pass


class NormalizedVersion(object):
    """
    Normalize a version string.

    Args:
        activity_version (str): the version string

    Raises:
        :exc:`InvalidVersionError`

    Attributes:
        parts (list): the numeric parts of the version after normalization.
    """

    def __init__(self, activity_version):
        self._activity_version = activity_version
        self.parts = []
        self._local = None

        if not isinstance(self._activity_version, str):
            raise InvalidVersionError(self._activity_version)

        match = VERSION_RE.search(self._activity_version)
        if not match:
            raise InvalidVersionError(self._activity_version)

        groups = match.groupdict()

        version = self._parse_version(groups['version'])
        self.parts.append(version)

        if groups['extraversion'] not in ('', None):
            versions = self._parse_extraversions(groups['extraversion'][1:])
            self.parts.extend(versions)

        self._local = groups['local']

    def _parse_version(self, version_string):
        """Verify that there is no leading zero and convert to integer.

        Keyword arguments:
        version -- string to be parsed

        Return: Version

        """
        if len(version_string) > 1 and version_string[0] == '0':
            raise InvalidVersionError("Can not have leading zero in segment"
                                      " %s in %r" %
                                      (version_string, self._activity_version))

        return int(version_string)

    def _parse_extraversions(self, extraversion_string):
        """Split into N versions and convert them to integers, verify
        that there are no leading zeros and drop trailing zeros.

        Keyword arguments:
        extraversion -- 'N.N.N...' sequence to be parsed

        Return: List of extra versions

        """
        nums = []
        for n in extraversion_string.split("."):
            if len(n) > 1 and n[0] == '0':
                raise InvalidVersionError("Can not have leading zero in "
                                          "segment %s in %r"
                                          % (n, self._activity_version))
            nums.append(int(n))

        while nums and nums[-1] == 0:
            nums.pop()

        return nums

    def __str__(self):
        version_string = '.'.join(str(v) for v in self.parts)
        if self._local is not None:
            version_string += self._local
        return version_string

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def _cannot_compare(self, other):
        raise TypeError("Can not compare %s and %s"
                        % (type(self).__name__, type(other).__name__))

    def __eq__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts < other.parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)
