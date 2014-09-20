import sys
import logging

import device as cordova_Device
import accelerometer as cordova_Accelerometer
import camera as cordova_Camera
import network as cordova_Network
import dialog as cordova_Dialog
import globalization as cordova_Globalization


class callCordova(object):

    def call_to_cordova(self, plugin_name, function_name, args, parent,
                        request):
        try:
            plugin_filecode = getattr(sys.modules[__name__],
                                      "cordova_" + plugin_name)
            # the class name for the plugin must be same as the plugin name
            plugin_class = getattr(plugin_filecode, plugin_name)()
            # The service method same as that described for the given class
            service_method = getattr(plugin_class, function_name)
            # give the parameters in args
            result = service_method(args, parent, request)
            return result
        except:
            parent._client.send_error(request, "The native func doesn't exist")
