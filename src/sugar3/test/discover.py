# Copyright (C) 2013, Daniel Narvaez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
UNSTABLE.
"""

import argparse
import sys
import os
import tempfile
import shutil
import unittest


def main():
    parser = argparse.ArgumentParser(description="Discover unit tests.")
    parser.add_argument("tests_dir", help="Base tests directory")
    args = parser.parse_args()

    temp_dir = tempfile.mkdtemp()

    os.chdir(args.tests_dir)
    os.environ["TMPDIR"] = temp_dir

    try:
        test = unittest.defaultTestLoader.discover(".")
        result = unittest.TextTestRunner().run(test)
        if not result.wasSuccessful():
            sys.exit(1)
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
