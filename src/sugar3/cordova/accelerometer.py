import time


class Accelerometer(object):
    def getCurrentAcceleration(self, args, parent, request):
        timestamp = time.time()
        ACCELEROMETER_DEVICE = '/sys/devices/platform/lis3lv02d/position'
        try:
            fh = open(ACCELEROMETER_DEVICE,"r")
            string = fh.read()
            xyz = string[1:-2].split(',')
            fh.close()
            accelerometer_obj = {'x': int(xyz[0]), 'y': int(xyz[1]),
                                 'z': int(xyz[2]), 'timestamp': timestamp,
                                 'keepCallback': True}
            parent._client.send_result(request, accelerometer_obj)
        except:
            accelerometer_obj = {'x': 0, 'y': 0, 'z': 0,
                                 'timestamp': timestamp,
                                 'keepCallback': True}
            parent._client.send_error(request, "Accelerometer File not found")
