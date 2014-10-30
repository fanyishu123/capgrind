import math
import numpy
import matplotlib
import matplotlib.gridspec as gridspec

from others import HUD

RL_DIM = {0 : 5.5, 1 : 1.1, 2 : 1.1}

AXES = { 0 : 'Z', 1 : 'Y', 2 : 'X'}
MINOR_AXES = {}
MINOR_AXES_IND = {}

axes = [0,1,2]
for i in axes:
    s = axes[:]
    s.remove(i)
    MINOR_AXES[i] = (AXES[s[0]],AXES[s[1]])
    MINOR_AXES_IND[i] = (s[0], s[1])

class NoPointException(Exception): pass

class WM(object):

    def __init__(self, gui, template_name):
        self.gui = gui
        self.slots = []
        self.template_name = template_name
        self.fig = None

    def add_slot(self):
        self.slots.append(Slot(self))
        self.gui.event_handler.event(self, 'modified')

    def remove_unused_slots(self):
        self.slots = [slot for slot in self.slots if slot.adapters]
        self.gui.event_handler.event(self, 'modified')

    def change_adapters_slot(self, adapter, new_slot):
        adapter.slot.adapters.remove(adapter)
        new_slot.adapters.append(adapter)
        adapter.slot = new_slot
        self.gui.event_handler.event(self, 'modified')

    def get_images(self):
        return [slot.image for slot in self.slots]

    def reset_all_adapters(self, image):
        [slot.reset() for slot in self.slots if slot.image == image]

    def __str__(self):
        return self.template_name


class SlotNode(object):

    def __init__(self, wm, image=None):
        self.wm = wm
        self.image = image
        self.adapters = []
        self.rois = []

    def index(self):
        return self.wm.slots.index(self)

    def set_image(self, identifier):
        self.image = self.wm.gui.image_db.get_image(identifier)
        self.wm.gui.event_handler.event(self.wm, 'modified')
        self.reset()

    def reset(self):
        [adapter.reset() for adapter in self.adapters]

    def update(self):
        [adapter.update() for adapter in self.adapters]

class Slot(SlotNode):

    def __init__(self, wm, image = None):
        SlotNode.__init__(self, wm, image)
        self.point = None
        self.zoom_level = 1
        self.b_value = 0

    def set_point(self, point):
        self.point = point
        [a2.set_slice() for a2 in self.adapters]
        self.update()

    def set_zoom_level(self, zoom_level):
        self.zoom_level = min(10, max(0.5, zoom_level))
        [a2.set_zoom_level() for a2 in self.adapters]
        self.update()

    def set_bvalue(self, num):
        self.b_value = min(max(num, 0), self.image.shape[-1]-1)
        self.update()

    def n_bvalues(self):
        return self.image.shape[-1]

    def __str__(self):
        return ("Z: %.2f" % self.zoom_level) + (", B: %d" % self.b_value)


class ViewNode(object):

    def __init__(self, slot, axes):
        self.slot = slot
        self.axes = axes

    def change_slot(self, slot):
        self.slot.wm.change_adapters_slot(self,slot)
        self.reset()

    def reset(self): pass
    def update(self): pass

class View(ViewNode):

    def __init__(self,  slot, axes, norm=0, slice=0):
        ViewNode.__init__(self, slot, axes)
        self.norm = norm
        self.slice = slice

    def change_projection(self,norm_i):
        self.norm = norm_i
        self.slice = 10
        self.reset()

    def toggle_projection(self):
        self.change_projection((self.norm+1)%3)
        self.reset()

    def set_slice(self):
        self.slice = self.slot.point[self.norm]

    def set_this_slice(self, num):
        self.slice = min(max(num, 0), self.slot.image.shape[self.norm]-1)
        self.update()

    def n_slices(self):
        return self.slot.image.shape[self.norm]

    def get_axes_labels(self):
        return (MINOR_AXES[self.norm][0], MINOR_AXES[self.norm][1])

    def get_axes_aspect(self):
        x_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][1]]
        y_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][0]]
        return (x_mm_dim/y_mm_dim)

    def get_updated_point(self, x=None, y=None, slice=None):
        shape = self.get_shape()
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]
        if x!=None and y!=None:
            x = min(max(x, 0), shape[minor1]-1)
            y = min(max(y, 0), shape[minor2]-1)
        else:
            x = self.slot.point[minor1]
            y = self.slot.point[minor2]
        if slice!=None:
            slice = min(max(slice, 0), shape[major]-1)
        else:
            slice = self.slot.point[major]
        point = [0,0,0]
        point[major], point[minor1], point[minor2] = slice, x, y
        return point

    def get_point_xy(self):
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]
        return self.slot.point[minor1], self.slot.point[minor2]

    def get_lims_xy(self):
        shape = self.get_shape()
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]
        return shape[minor1], shape[minor2]

    def view_to_tuple(self):
        return (self.norm, self.slice)

    def view_from_tuple(self, t):
        View.__init__(self, *t)
        self.reset()

    def _has_image(self):
        return self.slot.image != None

    def _has_point(self):
        return self.slot.point != None

    def get_shape(self):
        return self.slot.image.shape

    def get_data(self):
        return self.slot.image.get_slice(self.norm, self.slice, self.slot.b_value)

# TODO: Techinically HUD shouldn't be multiply inherited because it requires ViewNode and some of View's
# TODO: properties, but this is not enforced (diamond).

class AxesAdapter(View, HUD):

    def __init__(self, slot, axes, view_tuple=()):
        View.__init__(self, slot, axes, *view_tuple)
        HUD.__init__(self)

    def reset(self):
        self.reset_image()

    def update(self):
        self.update_image()

    def reset_image(self):
        msg_visible, aspect = False, self.get_axes_aspect()
        del self.axes.images[:]
        if self._has_image():
            self.axes.imshow(self.get_data(), origin='lower', zorder=-1, **self.slot.image.kwargs)
        else:
            msg_visible, aspect = True, 1.0

        self.axes.set_aspect(aspect)
        self.HUD_draw(msg_visible)

    def update_image(self):
        if self._has_image():
            im = self.axes.get_images()[0]
            im.set_data(self.get_data())
            kwargs = self.slot.image.kwargs
            im.norm.vmin,im.norm.vmax = kwargs['vmin'], kwargs['vmax']
            self.draw_crosshair()

    # start adapter methods...

    def get_rel(self, cur_y, total, start_y, start, min_y, max_y):
        return start+(start_y - cur_y)/(max_y - min_y)*total

    def start_crosshair(self, start_x, start_y, event): pass

    def drag_crosshair(self, event):
        self.slot.set_point(self.get_updated_point(event.xdata, event.ydata, self.slice))

    def end_crosshair(self): pass

    def start_pan(self, start_x, start_y, event_button):
        self._button_pressed = event_button
        self.axes.start_pan(start_x, start_y, event_button)

    def drag_pan(self, event):
        self.axes.drag_pan(self._button_pressed, event.key, event.x, event.y)
        self.draw_crosshair()

    def end_pan(self):
        self.axes.end_pan()
        self._button_pressed = None

    def start_slice(self, start_x, start_y, event):
        x1, y1, x2, y2 = self.axes.bbox.extents
        self.temp = dict(start_y=start_y, start=self.slice, min_y=y1, max_y=y2)

    def drag_slice(self, event):
        slice = self.get_rel(event.y, self.n_slices(), **self.temp)
        self.set_this_slice(slice)

    def end_slice(self): pass

    def start_gslice(self, start_x, start_y, event):
        if not self._has_point(): raise NoPointException("No point defined!")
        self.start_slice(start_x, start_y, event)

    def drag_gslice(self, event):
        self.drag_slice(event)
        self.slot.set_point(self.get_updated_point(slice=self.slice))

    def end_gslice(self):
        self.end_slice()

    def start_gzoom(self, start_x, start_y, event):
        if not self._has_point(): raise NoPointException("No point defined!")
        y1, y2 = self.axes.get_ylim()
        self.temp = dict(start_y=start_y, start=self.slot.zoom_level, min_y=y1, max_y=y2)

    def drag_gzoom(self, event):
        zoom_level = self.get_rel(event.y, 10, **self.temp)
        self.slot.set_zoom_level(zoom_level)

    def set_zoom_level(self):
        level = self.slot.zoom_level
        cx, cy = self.get_point_xy()
        wx, wy = self.get_lims_xy()
        nx1, nx2 = cx-wx/(2*level), cx+wx/(2*level)
        ny1, ny2 = cy-wy/(2*level), cy+wy/(2*level)
        self.axes.set_xlim([nx1,nx2])
        self.axes.set_ylim([ny1,ny2])

    def end_gzoom(self): pass

    def start_bvalue(self, start_x, start_y, event):
        x1, y1, x2, y2 = self.axes.bbox.extents
        self.temp = dict(start_y=start_y, start=self.slot.b_value, min_y=y1, max_y=y2)

    def drag_bvalue(self, event):
        b_value = self.get_rel(event.y, self.slot.n_bvalues(), **self.temp)
        self.slot.set_bvalue(b_value)

    def end_bvalue(self): pass

    # end adapter methods...

    def get_display_str(self):
        d1 = "none/" if not self._has_point() else "%dx%dx%dx(%d)/" % (tuple(self.slot.point)+(self.slot.b_value,))
        d2 = "none" if not self._has_image() else "%dx%dx%dx(%d)" % tuple(self.get_shape())
        return d1+d2

    def get_display_minor_str(self, add_total=True):
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]

        s = ["","","",""]
        s[minor1] = "[%d-%d]x" % self.axes.get_xlim()
        s[minor2] = "[%d-%d]x" % self.axes.get_ylim()
        s[major] = "%dx" % int(self.slice)
        s[-1] = "(%d)" % int(self.slot.b_value)
        s = "".join(s)

        if add_total: s = s + "none" if not self._has_image() else ("/%dx%dx%dx(%d)" % tuple(self.get_shape()))
        return s

    def __str__(self):
        return self.get_display_minor_str(False)


TEMPLATES = {
    '1x1' : ((1,1), [(0,0)], [0], [()]),
    '1x2' : ((1,2), [(0,0),(0,1)], [0,1], [(),()]),
    '2x1' : ((2,1), [(0,0),(1,0)], [0,1], [(),()]),
    '2x2' : ((2,2), [(0,0),(0,1),(1,0),(1,1)], [0,0,1,1], [(),(),(),()]),
    '3x2' : ((3,2), [(0,0),(0,1),(1,0),(1,1),(2,0),(2,1)], [0,1,0,1,0,1], [(),(),(),(),(),()]),
    '2x3' : ((2,3), [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)], [0,0,0,1,1,1], [(),(),(),(),(),()]),
    '3x3' : ((3,3), [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0),(2,1),(2,2)], [0,0,0,1,1,1,2,2,2],
            [(),(),(),(),(),(),(),(),()]),
    '2x1s' : ((2,2), [(slice(None),0),(0,1),(1,1)], [0,0,0], [(),(),()]),
    '1sx2' : ((2,2), [(0,0),(1,0),(slice(None),1)], [0,0,0], [(),(),()]),
}

ACTION_TEMPLATES = ('FULLSCREEN', 'PROJECTION', 'SLICES')

class UndefinedException(Exception):
    pass

def smallest_containing_square(n):
    return numpy.ceil(numpy.sqrt(n)).astype(int)

def filter_sources(sources, n_to):
    sources, n_from = numpy.copy(sources), len(sources)
    # If we need to add sources, append None as new sources
    if n_from < n_to:
        return numpy.append(sources, [None]*(n_to-n_from))
    # If we need to remove sources, cut from the end
    elif n_from > n_to:
        # Numpy doesn't overwrite comparison with None
        has_image = [source for source in sources if source != None]
        if len(has_image) <= n_to:
            return numpy.append(has_image, [None]*(n_to-len(has_image)))
        else:
            return has_image[:n_to]
    else:
        return sources


def transition(gui, to_template, old_slots, action_adapter=None, n_to=None):
    if not action_adapter and not n_to:
        return static_transition(gui,old_slots,to_template)
    elif action_adapter:
        return action_transition(gui,to_template,action_adapter)
    elif n_to:
        return dynamic_transition(gui,old_slots,to_template,n_to)
    else:
        raise UndefinedException("Transition not defined.")


def static_transition(gui, old_slots, to_template):
    print "=> Static transition"
    grid_spec, grid_inds, slot_inds, view_props = TEMPLATES[to_template]
    transition_images = filter_sources(old_slots, len(set(slot_inds)))

    return WM_generator(gui, to_template, transition_images, grid_spec, grid_inds, slot_inds, view_props)

def action_transition(gui, to_template, action_adapter):
    print "=> Action transition"
    grid_spec, grid_inds, slot_inds, view_props = None, None, None, None
    transition_images = [action_adapter.slot.image]

    if to_template == 'FULLSCREEN':
        grid_spec, grid_inds, slot_inds, view_props = (1,1),[(0,0)],[0],[action_adapter.view_to_tuple()]
    elif to_template == 'PROJECTION':
        point = action_adapter.slot.point if action_adapter.slot.point else [0,0,0]
        grid_spec, grid_inds, slot_inds = (1,3), [(0,0),(0,1),(0,2)], [0]*3
        view_props = [(i,point[i]) for i in range(3)]
    elif to_template == 'SLICES':
        n = action_adapter.n_slices()-1
        side = 4
        max_slices = side*side
        slice_inds = [int(round(n/(max_slices-1.0)*i)) for i in range(max_slices)]
        grid_spec, slot_inds = (side,side), [0]*max_slices
        grid_inds = [(i,j) for i in range(side) for j in range(side)]
        view_props = [(action_adapter.norm,sl) for sl in slice_inds]
    else:
        raise UndefinedException("Transition to " + to_template + " not defined.")

    return WM_generator(gui, to_template, transition_images, grid_spec, grid_inds, slot_inds, view_props)

def dynamic_transition(gui, old_sources, to_template, to_n):
    print "=> Dynamic transition"
    grid_spec, grid_inds, slot_inds, view_props = None, None, None, None
    transition_images = filter_sources(old_sources, to_n)

    if to_template == 'PROJECTION':
        grid_spec, slot_inds = (to_n,3), [i for i in range(to_n) for j in range(3)]
        grid_inds = [(i,j) for i in range(to_n) for j in range(3)]
        view_props = [(j,0) for i in range(to_n) for j in range(3)]
    elif to_template == 'FULLSCREEN':
        side = smallest_containing_square(to_n)
        rows = int(math.ceil(float(to_n)/side))
        grid_spec, slot_inds = (rows,side), [i for i in range(to_n)]
        grid_inds = [(i/side,i%side) for i in range(to_n)]
        view_props = [() for i in range(to_n)]
    elif to_template == 'SLICES':
        raise UndefinedException("Transition from to " + to_template + " not defined.")
    else:
        pass

    return WM_generator(gui, to_template, transition_images, grid_spec, grid_inds, slot_inds, view_props)


def WM_generator(gui, to_template, transition_images, grid_spec, grid_inds, slot_inds, view_props):

    grid_generator = gridspec.GridSpec(*grid_spec)
    cells = [grid_generator[loc] for loc in grid_inds]

    wm = WM(gui, to_template)
    wm.fig = matplotlib.figure.Figure(figsize=(5,4), dpi=100)
    slots = [Slot(wm,im) for im in transition_images]
    map_to_slot = [slots[ind] for ind in slot_inds]
    wm.slots.extend(slots)

    for cell, slot, view_prop in zip(cells, map_to_slot, view_props):
        ax = wm.fig.add_subplot(cell)
        ax2 = AxesAdapter(slot, ax, view_prop)
        ax.adapter = ax2
        slot.adapters.append(ax2)
        ax2.reset_image()

    return wm
