import os
from gi.repository import Gtk
import base64
import pygame
import pygame.camera
from pygame.locals import *

from jarabe.journal.objectchooser import ObjectChooser

import logging

from sugar3.datastore import datastore


class Camera:

    def image_chooser(self, args, parent, request):
        chooser = choose_image(parent, request)
        chooser.show_image_chooser(parent)

    def webcam(self, args, parent, request):
        filename = pygame_camera()
        fh = open(filename)
        string = fh.read()
        fh.close()
        encoded_string = base64.b64encode(string)
        parent._client.send_result(request, encoded_string)


class choose_image:
    def __init__(self, parent, request):
        self.parent = parent
        self.request = request

    def chooser_response_cb(self, chooser, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            object_id = chooser.get_selected_object_id()
            selected_object = datastore.get(object_id)
            image_path = selected_object.file_path
            fh = open(image_path)
            string = fh.read()
            fh.close()
            encoded_string = base64.b64encode(string)
            chooser.destroy()
            self.parent._client.send_result(self.request, encoded_string)
        else:
            chooser.destroy()
            self.parent._client.send_result(self.request, encoded_string)

    def show_image_chooser(self, parent):
        chooser = ObjectChooser(parent._activity, what_filter='Image')
        chooser.connect('response', self.chooser_response_cb)
        chooser.show()


def pygame_camera():
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        pygame.camera.init()
        screen = pygame.display.set_mode((640, 480), pygame.NOFRAME)
        pygame.display.set_caption("Click mouse anywhere to click photograph")
        camlist = pygame.camera.list_cameras()
        if camlist:
            cam = pygame.camera.Camera(camlist[0], (640, 480))
        cam.start()
        quit_loop = 0
        cam_image = cam.get_image()
        while quit_loop == 0:
            cam_image = cam.get_image()
            screen.blit(cam_image, (0, 0))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE) or (event.type == MOUSEBUTTONDOWN):
                    # save the image
                    cam.stop()
                    pygame.display.quit()
                    quit_loop = 1
        filename = "/home/broot/Documents/image" + snapshot_name() + ".jpg"
        pygame.image.save(cam_image, filename)
        return filename


def snapshot_name():
    # Return a string of the form yyyy-mm-dd-hms
    from datetime import datetime
    today = datetime.today()
    y = str(today.year)
    m = str(today.month)
    d = str(today.day)
    h = str(today.hour)
    mi = str(today.minute)
    s = str(today.second)
    return '%s-%s-%s-%s%s%s' % (y, m, d, h, mi, s)
