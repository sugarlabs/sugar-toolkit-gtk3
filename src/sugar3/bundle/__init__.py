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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
# MA  02110-1301 USA

'''
Activity Metadata
=================

Your `activity/activity.info` file must have these metadata keys after
an `[Activity]` header on the first line:

* `name` - the name of the activity, shown by Sugar in the list of
  installed activities, e.g. Browse,

* `activity_version` - the version of the activity, e.g. 1, 1.2,
  1.2.3, 1.2.3-country, or 1.2.3~developer,

* `bundle_id` - the activity bundle identifier, using [Java package
  naming conventions]
  (http://en.wikipedia.org/wiki/Java_package#Package_naming_conventions),
  should conform to the [D-Bus specification for message protocol
  names]
  (http://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names)
  (hyphens are not allowed), usually an organisation or individual domain name
  in reverse order, e.g. `org.sugarlabs.Name`,

* `license` - an identifier for the software license of the bundle,
  either a `Fedora License Short Name`_, (e.g. GPLv3+) or an `SPDX
  License Identifier`_, with an optional `or later version` suffix,
  e.g. `GPL-3.0+`, and multiple licenses are to be separated with
  semicolons,

* `icon` - the icon file for the activity, shown by Sugar in the list
  of installed activities,

* `exec` - how to execute the activity, e.g.
  `sugar-activity3 module.Class` (For activities written for Python 3),
  `sugar-activity module.Class` (For activities written for Python 2)

Optional metadata keys are;

* `summary` - a short summary of the activity that may be displayed in
  the List or Home Views,

* `mime_types` - list of MIME types supported by the activity,
  separated by semicolons.  Your `read_file` method must be able to read
  files of these MIME types.  Used to offer your activity when opening a
  downloaded file or a journal object.

* `url` - link to a home page or user documentation on
  https://help.sugarlabs.org/,

* `repository` - link to repository for activity code, for use by git clone,

* `single_instance` - if yes, only a single instance of an activity
  should be started at any one time, and if another instance is requested
  the existing instance shown,

* `max_participants` - maximum participants for sharing an activity,

* `tags` - a semicolon or whitespace delimited list of keywords that
   describe the activity. Suggested keywords are Programming,
   Robotics, Internet, Science, Maths, Language, Geography, Game, Documents,
   Music, Media, Art, Teacher, or System,

* `show_launcher` - if set to "no", the activity is not shown in list view,

Deprecated metadata keys are;

* `category` or `categories` - aliases for `tags`,

* `website` - alias for `url`,

* `update_url` - the updater no longer uses this.

.. _SPDX License Identifier: http://spdx.org/licenses/
.. _Fedora License Short Name:
  https://fedoraproject.org/wiki/Licensing:Main?rd=Licensing#Good_Licenses

AppStream Metadata
==================

AppStream is a standard, distribution independent package metadata.
For Sugar activities, the AppStream metadata is automatically exported
from the activity.info file by the bundlebuilder during the install
step.

In order to be compliant with AppStream, activities must have the
following metadata fields under the [Activity] header (of the
`activity.info` file):

* `metadata_license` - license for screenshots and description.  AppStream
  requests only using one of the following: `CC0-1.0`, `CC-BY-3.0`,
  `CC-BY-SA-3.0` or `GFDL-1.3`

* `description` - a long (multi paragraph) description of your application.
  This must be written in a subset of HTML.  Only the p, ol, ul and li tags
  are supported.

Optional metadata key:

* `screenshots` - a space separated list of screenshot URLs.  PNG or JPEG files
  are supported.

Example `activity.info`
-----------------------

.. code-block:: ini

    [Activity]
    name = Browse
    bundle_id = org.laptop.WebActivity
    exec = sugar-activity3 webactivity.WebActivity -s
    activity_version = 200
    icon = activity-web
    max_participants = 100
    summary = Surf the world!

    license = GPLv2+;LGPLv2+;GPLv3+
    repository = https://github.com/sugarlabs/browse-activity.git
    url = https://help.sugarlabs.org/en/browse.html
    tags = Utilities;Internet

    metadata_license = CC0-1.0
    description:
        <p>
        Surf the world! Here you can do research, watch educational videos,
        take online courses, find books, connect with friends and more.
        Browse is powered by the WebKit2 rendering engine with the Faster
        Than Light javascript interpreter - allowing you to view the
        full beauty of the web.
        </p>
        <p>To help in researching, Browse offers many features:</p>
        <ul>
            <li>
            Bookmark (save) good pages you find - never loose good resources
            or forget to add them to your bibliography
            </li>
            <li>
            Bookmark pages with collaborators in real time - great for
            researching as a group or teachers showing pages to their class
            </li>
            <li>
            Comment on your bookmarked pages - a great tool for making curated
            collections
            </li>
        </ul>
    screenshots = https://people.sugarlabs.org/sam/activity-ss/browse-1-1.png https://people.sugarlabs.org/sam/activity-ss/browse-1-2.png
'''
