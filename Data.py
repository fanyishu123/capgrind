#
#   The Data Model
#

from Globals import RL_DIM, D, trigger_update

import os
import numpy
import matplotlib.patches

RL_spec = "x".join([str(s)+"mm" for s in RL_DIM.values()[:-1]])

add_i = lambda s1, s2 : map(lambda t:t[0]+t[1], zip(s1, s2))
del_i = lambda s1, s2 : map(lambda t:t[0]-t[1], zip(s1, s2))
ubox_i = lambda t1, t2 : (min(t1[0],t2[0]),max(t1[1],t2[1]))
max_bbox = lambda b1, b2 : [ubox_i(t1,t2) for t1,t2 in zip(b1,b2)]
roi_bbox = lambda c, r : zip(del_i(c, r), add_i(c, r))
array_bbox = lambda o, s : zip(o, add_i(o, s))

def get_next(names, prefix):
    i = 1
    while prefix+" "+str(i) in names:
        i+=1
    return prefix+" "+str(i)

# A collection of Spaces
class Spaces(object):

    def __init__(self, model, spaces=()):
        self.model = model
        self.spaces = []
        [self.add_space(s) for s in spaces]

    def add_space(self, space):
        space.spaces = self
        self.spaces.append(space)
        space.key = get_next([space.key for space in self.spaces], "Space")
        self.updated(space, spaces_container=True)

    def get_space(self, space_key):
        return [space for space in self.spaces if space.key == space_key][0]

    def remove_space(self, space):
        space.spaces = None
        self.spaces.remove(space)
        self.updated(space, spaces_container=True)

    def updated(self, space, spaces_container=False):
        self.model.spaces_updated(space, spaces_container)

#TODO: this should define the dimensions

# Represents a physical hyperspace
class Space(object):

    def __init__(self, key="", arrays=()):
        self.spaces = None
        self.key = key
        self.arrays = []
        [self.add_array(a) for a in arrays]

    def get_bbox(self):
        return ((0,100),)*D if not self.arrays else reduce(max_bbox, [array.bbox for array in self.arrays])

    @trigger_update
    def add_array(self, array):
        array.space = self
        self.arrays.append(array)

    @trigger_update
    def remove_array(self, array):
        array.space = None
        self.arrays.remove(array)

    def index(self):
        return self.spaces.spaces.index(self)

    def __str__(self):
        return self.key

    def updated(self):
        if self.spaces: self.spaces.updated(self)


# Data array in the physical space
class Data(object):

    def __init__(self, bbox):
        self.space = None
        self.bbox = bbox

    def contains(self, point, skip):
        return min([self.bbox[i][0] <= point[i] < self.bbox[i][1] for i in range(len(self.bbox)) if i not in skip])

    def relative(self, point):
        return del_i(point, [t[0] for t in self.bbox])

    def origin(self):
        return tuple([t[0] for t in self.bbox])

    def updated(self):
        if self.space: self.space.updated()


class DataArray(Data):
    def __init__(self, fn, origin=(0,)*D, cmap='jet', alpha=1.0, vmin=None, vmax=None):
        self.fn = os.path.basename(fn)
        self.image = numpy.load(fn, mmap_mode='r')
        super(DataArray, self).__init__(array_bbox(origin, self.image.shape))
        self.vmin = vmin if vmin else self.image.min().item()
        self.vmax = vmax if vmax else self.image.max().item()
        self.cmap, self.alpha = cmap, alpha

    @trigger_update
    def set_cmap(self, cmap):
        self.cmap = cmap

    @trigger_update
    def set_vlims(self, vmin, vmax):
        self.vmin, self.vmax = vmin, vmax

    def get_slice(self, proj, to=()):
        proj = self.relative(proj)
        s = lambda i : slice(None,None,None) if i in to else proj[i]
        subspace = [s(i) for i in range(len(proj))]
        return self.image[subspace].T

    def __str__(self):
        return self.fn

class Image(DataArray):
    def __init__(self, fn, origin=(0,)*D, cmap='jet', alpha=1.0, vmin=None, vmax=None):
        super(Image, self).__init__(fn, origin=origin, cmap=cmap, alpha=alpha, vmin=vmin, vmax=vmax)

class DataROI(DataArray):
    def __init__(self, fn, origin=(0,)*D):
        super(DataROI, self).__init__(fn, origin=origin, cmap='Greens', alpha=0.75, vmin=0.0, vmax=1.0)
        # Normalize to True/False by cutting from the middle
        mask = self.image < (self.image.max() - self.image.min())/2.0
        self.image = numpy.ma.masked_array(numpy.ones(self.image.shape), mask=mask)

class DataOverlay(DataArray):
    def __init__(self, fn, origin=(0,)*D):
        super(DataOverlay, self).__init__(fn, origin=origin, cmap='Oranges', alpha=0.75, vmin=0.0, vmax=1.0)
        mask = self.image < (self.image.max() - self.image.min())/2.0
        self.image = numpy.ma.masked_array(numpy.ones(self.image.shape), mask=mask)

class AbstractROI(Data):

    def __init__(self, c=(0,)*D, r=(0,)*D):
        super(AbstractROI, self).__init__(roi_bbox(c,r))
        self.c, self.r = c, r

    # Abstract ROIs can cheat by defining [v_1 v_1], not [v_1 v_1), as bbox, so that v_1 belongs in bbox
    def contains(self, point, skip):
        return min([self.bbox[i][0] <= point[i] <= self.bbox[i][1] for i in range(len(self.bbox)) if i not in skip])

    def get_patch(self, proj, to1, to2): pass

    @trigger_update
    def set_roi_axes(self, c, r):
        self.c, self.r = c, r
        self.bbox = roi_bbox(c,r)

    @trigger_update
    def update_roi_axes_r(self, a, r):
        self.r[a] = r
        self.bbox[a] = (self.c[a]-self.r[a], self.c[a]+self.r[a])

    def get_roi_axes_r(self, a):
        return self.r[a]


class HyperRectangleROI(AbstractROI):

    def get_patch(self, proj, to1, to2):
        cx, cy = self.c[to1], self.c[to2]
        rx, ry = self.r[to1], self.r[to2]
        xmin, xmax = cx - rx, cx + rx
        ymin, ymax = cy - ry, cy + ry
        #print "Rectangle: ", (xmin, xmax), (ymin, ymax)
        return matplotlib.patches.Rectangle((xmin, ymin), xmax-xmin, ymax-ymin, color='green', alpha=0.75)

class HyperEllipseROI(AbstractROI):

    def get_patch(self, proj, to1, to2):
        cx, cy = self.c[to1], self.c[to2]
        rx, ry = self.r[to1], self.r[to2]
        # TODO: this is for advanced indexing, need something more efficient
        np_c, np_r, np_p = numpy.array(self.c), numpy.array(self.r), numpy.array(proj)
        # Create index set for the interpretation r_i=0 => x_i=0 in origo centered ellipse
        i = np_r != 0
        i[to1] = False
        i[to2] = False
        # Get slice of the ellipse w.r.t to the hyperspace slice
        rem = numpy.sqrt(1-numpy.sum(((np_c[i]-np_p[i])/np_r[i]))**2)
        rx, ry = rx*rem, ry*rem
        #print "Ellipse: ", cx, cy, rx, ry
        return matplotlib.patches.Ellipse((cx, cy), rx*2.0, ry*2.0, color='green', alpha=0.75)

