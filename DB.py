import os
import numpy

#TODO: maybe we should give the event handler instead of the GUI ?...
class ImageDB(object):

    def __init__(self, gui, images):
        self.gui = gui
        self.images = dict(images)

    def add_image(self, identifier, image):
        self.images[identifier] = image
        self.gui.event_handler.event(self, 'modified')

    def del_images(self, *identifiers):
        for identifier in identifiers: del self.images[identifier]
        self.gui.event_handler.event(self, 'modified')

    def get_image(self, indentifier):
        return self.images[indentifier]

    def total_images(self):
        return len(self.images)

    def identifiers(self):
        return self.images.keys()

    #TODO: This is not very good, return an iterator instead
    def get_images(self):
        return tuple(self.images.values())

class Image_source(object):

    """ Do not directly access attributes, I may add all sorts of cool hacks to getters/setters
    to speed image lookups"""
    kws = (('interpolation', ('nearest',)),
           ('cmap', ('gray', 'jet', 'Blues_r',)) )
    kwls= (('Interpolation', ('Nearest',)),
           ('Colormap', ('Greyscale', 'Jet', 'Blue monotone')) )

    def __init__(self, fn, gui):
        self.gui = gui
        self.image = numpy.load(fn)
        self.fn = os.path.basename(fn)
        self.shape = self.image.shape
        self.vmin = self.image.min()
        self.vmax = self.image.max()
        self.kwargs = dict(interpolation='nearest', cmap='jet', vmin=self.vmin, vmax=self.vmax)

    def __str__(self):
        return self.fn

    def set_kwarg(self, **kwargs):
        for key, val in kwargs.items(): self.kwargs[key] = val
        self.gui.event_handler.event(self, 'modified')

    def set_option(self, key, val):
        self.kwargs[key] = val
        self.gui.event_handler.event(self, 'modified')

    def get_kwarg(self, key):
        return self.kwargs[key]

    def get_shape(self):
        return self.shape

    def get_slice(self, slice_index, slice_value, b_value):
        d = 4
        x = [slice(None,None,None)]*d
        x[slice_index] = slice_value
        x[-1] = b_value
        # Image[:,...,:,slice_value,:,...,:,b_value]
        # slice_index --->
        return self.image[x].T
