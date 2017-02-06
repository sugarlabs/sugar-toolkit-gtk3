from gi.repository import Gio
import jarabe.config
import logging

import os
from gettext import gettext as _


_OFW_TREE = '/ofw'
_PROC_TREE = '/proc/device-tree'
_DMI_DIRECTORY = '/sys/class/dmi/id'
_SN = 'serial-number'
_MODEL = 'openprom/model'
_not_available = _('Not available')


class Device:
    def sugar_version(self, args, parent, request):
        parent._client.send_result(request, jarabe.config.version)

    def sugar_model(self, args, parent, request):
        settings = Gio.Settings('org.sugarlabs.extensions.aboutcomputer')
        hardware_model = settings.get_string('hardware-model')
        parent._client.send_result(request, hardware_model)

    def sugar_uuid(self, args, parent, request):
        uuid = get_serial_number()
        parent._client.send_result(request, uuid)


def _parse_firmware_number(firmware_no):
    if firmware_no is None:
        firmware_no = _not_available
    else:
        # try to extract Open Firmware version from OLPC style version
        # string, e.g. "CL2   Q4B11  Q4B"
        if firmware_no.startswith('CL'):
            firmware_no = firmware_no[6:13]
    return firmware_no


def get_firmware_number():
    firmware_no = None
    if os.path.exists(os.path.join(_OFW_TREE, _MODEL)):
        firmware_no = _read_file(os.path.join(_OFW_TREE, _MODEL))
        firmware_no = _parse_firmware_number(firmware_no)
    elif os.path.exists(os.path.join(_PROC_TREE, _MODEL)):
        firmware_no = _read_file(os.path.join(_PROC_TREE, _MODEL))
        firmware_no = _parse_firmware_number(firmware_no)
    elif os.path.exists(os.path.join(_DMI_DIRECTORY, 'bios_version')):
        firmware_no = _read_file(os.path.join(_DMI_DIRECTORY, 'bios_version'))
        if firmware_no is None:
            firmware_no = _not_available
    return firmware_no


def get_serial_number():
    serial_no = None
    if os.path.exists(os.path.join(_OFW_TREE, _SN)):
        serial_no = _read_file(os.path.join(_OFW_TREE, _SN))
    elif os.path.exists(os.path.join(_PROC_TREE, _SN)):
        serial_no = _read_file(os.path.join(_PROC_TREE, _SN))
    if serial_no is None:
        serial_no = _not_available
    return serial_no


def get_build_number():
    build_no = _read_file('/boot/olpc_build')

    if build_no is None:
        build_no = _read_file('/etc/redhat-release')

    if build_no is None:
        try:
            popen = subprocess.Popen(['lsb_release', '-ds'],
                                     stdout=subprocess.PIPE)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        else:
            build_no, stderr_ = popen.communicate()

    if build_no is None or not build_no:
        build_no = _not_available

    return build_no


def _read_file(path):
    if os.access(path, os.R_OK) == 0:
        return None

    fd = open(path, 'r')
    value = fd.read()
    fd.close()
    if value:
        value = value.strip('\n')
        return value
    else:
        _logger.debug('No information in file or directory: %s', path)
        return None
