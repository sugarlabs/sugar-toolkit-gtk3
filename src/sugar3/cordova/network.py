from jarabe.model import network
import dbus
import logging


_DBUS_SERVICE = 'org.sugarlabs.SugarServices'
_DBUS_PATH = '/org/sugarlabs/SugarServices'

proxy = None

network_type_name = None


class Network:

    def alert(self, args, parent, request):
        parent._client.send_result(request, network_type_name)


def get_network_type(parent, request):
    type_network = NetworkManagerObserver(parent, request)


def nm_status():
    global proxy
    if proxy is None:
        bus = dbus.SessionBus()
        proxy = bus.get_object(_DBUS_SERVICE, _DBUS_PATH)

    try:
        status = dbus.Interface(proxy, _DBUS_SERVICE).NMStatus()
        logging.debug(status)
        return status
    except Exception, e:
        logging.error('ERROR getting NM Status: %s' % e)
        return None

    if status in ['network-wireless-connected',
                  'network-wireless-disconnected',
                  'network-adhoc-1-connected',
                  'network-adhoc-1-disconnected',
                  'network-adhoc-6-connected',
                  'network-adhoc-6-disconnected',
                  'network-adhoc-11-connected',
                  'network-adhoc-11-disconnected']:
        return status
    else:
        return 'unknown'


# The Network Manager Class from sugar/extensions/deviceicon
class NetworkManagerObserver(object):
    def __init__(self):
        logging.error("Reached The Network Manager")
        self._bus = dbus.SystemBus()
        self._devices = {}
        self._netmgr = None
        # self._tray = tray

        try:
            obj = self._bus.get_object(network.NM_SERVICE, network.NM_PATH)
            self._netmgr = dbus.Interface(obj, network.NM_IFACE)
        except dbus.DBusException:
            logging.error('%s service not available', network.NM_SERVICE)
            return

        self._netmgr.GetDevices(reply_handler=self.__get_devices_reply_cb,
                                error_handler=self.__get_devices_error_cb)

        self._bus.add_signal_receiver(self.__device_added_cb,
                                      signal_name='DeviceAdded',
                                      dbus_interface=network.NM_IFACE)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                      signal_name='DeviceRemoved',
                                      dbus_interface=network.NM_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self.device123.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._update_state(properties['State'])

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._update_state(new_state)

    def _update_state(self, state):
        global network_type_name
        if state == network.NM_DEVICE_STATE_ACTIVATED:
            props1 = dbus.Interface(self.device123, dbus.PROPERTIES_IFACE)
            address = props1.Get(network.NM_DEVICE_IFACE, 'Ip4Address')
            device_type = props1.Get(network.NM_DEVICE_IFACE, 'DeviceType')

            if device_type == network.NM_DEVICE_TYPE_ETHERNET:
                logging.error("the network connection is ethernet")
                network_type_name = "ethernet"
            elif device_type == network.NM_DEVICE_TYPE_WIFI:
                logging.error("the network connection is wi-fi")
                network_type_name = "wifi"
            elif device_type == network.NM_DEVICE_TYPE_OLPC_MESH:
                logging.error("the network connection is olpc-mesh")
                network_type_name = "olpcmesh"
            elif device_type == network.NM_DEVICE_TYPE_MODEM:
                logging.error("the network connection is modem")
                network_type_name = "cellular"
        else:
            network_type_name = "none"
            logging.error("the network connection is none")

        logging.error(network_type_name)

    def __get_devices_reply_cb(self, devices):
        logging.error("__get_devices_reply_cb(self, devices)")
        for device_op in devices:
            self._check_device(device_op)

    def __get_devices_error_cb(self, err):
        logging.error("__get_devices_error_cb(self, err)")
        logging.error('Failed to get devices: %s', err)

    def _check_device(self, device_op):
        if device_op in self._devices:
            return

        nm_device = self._bus.get_object(network.NM_SERVICE, device_op)
        props = dbus.Interface(nm_device, dbus.PROPERTIES_IFACE)
        device_type = props.Get(network.NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.NM_DEVICE_TYPE_ETHERNET:
            self._devices[device_op] = "ethernet"
        elif device_type == network.NM_DEVICE_TYPE_WIFI:
            self._devices[device_op] = "wi-fi"
        elif device_type == network.NM_DEVICE_TYPE_OLPC_MESH:
            self._devices[device_op] = "olpc - mesh"
        elif device_type == network.NM_DEVICE_TYPE_MODEM:
            self._devices[device_op] = "cellular"
        else:
            logging.error("no connection")

        self.device123 = nm_device

        props.GetAll(network.NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__get_device_props_reply_cb,
                     error_handler=self.__get_device_props_error_cb)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=nm_device.object_path,
                                      dbus_interface=network.NM_DEVICE_IFACE)

    def __device_added_cb(self, device_op):
        self._check_device(device_op)

    def __device_removed_cb(self, device_op):
        if device_op in self._devices:
            device = self._devices[device_op]
            device.disconnect()
            del self._devices[device_op]


NetworkManagerObserver()
