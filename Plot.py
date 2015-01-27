#
#   Plotting front end
#

from Globals import D, RL_DIM, AXES, trigger_update

from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.artist
from matplotlib.lines import Line2D

from Templates import STATIC_TEMPLATES, DYNAMIC_TEMPLATES
import Data


# Constricts a point inside a given bounding box
constrict = lambda proj, bbox : [min(max(i, lims[0]), lims[1]-1) for i, lims in zip(proj,bbox)]

# Plotting front end component: interfaces the matplotlib figure to perform required actions
class FigureAdapter(object):

    @trigger_update
    def __init__(self, gui, template_name):
        self.gui = gui
        self.adapters = []
        self.template_name = template_name
        self._action_adapter = None

    def _add_adapters(self):
        TEMPLATES = DYNAMIC_TEMPLATES if self._action_adapter else STATIC_TEMPLATES
        grid_spec, grid_inds, space_inds, post_processing = TEMPLATES[self.template_name]
        grid_generator = gridspec.GridSpec(*grid_spec)
        cells = [grid_generator[loc] for loc in grid_inds]
        map_to_space = [self.gui.model.spaces.spaces[ind].key if 0 <= ind < len(self.gui.model.spaces.spaces) else ""
                        for ind in space_inds]
        for i, cell, space_key in zip(range(len(cells)), cells, map_to_space):
            self.gui.plotter.figure.add_subplot(cell)
            self.adapters.append(AxesAdapter(self, i, space_key))
        if post_processing and self._action_adapter:
            post_processing(self, self._action_adapter)

    def _del_adapters(self):
        self.adapters = []
        self.gui.plotter.figure.clf()

    @trigger_update
    def set_template(self, template_name, action_adapter=None):
        self.template_name = template_name
        self._action_adapter = action_adapter

    def updated(self):
        self._del_adapters()
        self._add_adapters()
        self.redraw_canvas()

    def spaces_updated(self, space, spaces_container=False):
        if spaces_container:
            cur_spaces = [space.key for space in self.gui.model.spaces.spaces]
            [a2.set_space("") for a2 in self.adapters if a2.space_key not in cur_spaces]
        else:
            [a2.updated() for a2 in self.adapters if a2.space_key == space.key]

    def redraw_canvas(self):
        if self.gui.plotter.figure.canvas:
            self.gui.plotter.figure.canvas.draw_idle()

    def iter_space(self, adapter):
        return [a2 for a2 in self.adapters if a2.space_key == adapter.space_key]


# Plotting front end component: contains a 2 dim slice specification of a D dim hyperspace
#                               or more accurately, restriction of f(R^D) into f(R^2)
#   .a1, a2                 - Sliced plane axes (indices)
#   .xmin, xmax, ymin, ymax - View limits in the sliced plane
#   .proj                   - Point in D-dimensions:
#                               .proj[.a1], .proj[.a2] - point in the sliced plane
#                               .proj[x], x != .a1/.a2 - slice specification

class Projection(object):

    def __init__(self):
        self.proj = [0]*D
        self.a1, self.a2 = 1, 2
        self.xmin, self.xmax = 0.0, 100.0
        self.ymin, self.ymax = 0.0, 100.0

    def get_bbox(self):
        return self.get_space().get_bbox()

    @trigger_update
    def reset_limits(self):
        (self.xmin, self.xmax), (self.ymin, self.ymax) = self.get_axes_limits()
        self.proj = constrict(self.proj, self.get_bbox())

    @trigger_update
    def reset_point(self):
        self.set_axes_point((self.xmax + self.xmin)/2.0, (self.ymax + self.ymin)/2.0)

    @trigger_update
    def set_space(self, space_key):
        self.space_key = space_key
        if self.space_key: self.reset_limits()

    @trigger_update
    def set_axes(self, a1, a2):
        self.a1, self.a2 = a1, a2
        self.reset_limits()

    def get_axes_labels(self):
        return AXES[self.a1], AXES[self.a2]

    def get_axes_aspect(self):
        return RL_DIM[self.a2]/RL_DIM[self.a1]

    def get_axes_limits(self):
        bbox = self.get_bbox()
        return bbox[self.a1], bbox[self.a2]

    @trigger_update
    def set_axes_limits(self, lims):
        self.xmin, self.xmax = lims[0]
        self.ymin, self.ymax = lims[1]

    def get_axes_point(self):
        return (self.proj[self.a1], self.proj[self.a2])

    @trigger_update
    def set_axes_point(self, i1, i2):
        self.set_proj_axis(self.a1, i1)
        self.set_proj_axis(self.a2, i2)

    @trigger_update
    def center_to_point(self):
        x,y = self.get_axes_point()
        wx, wy = (self.xmax-self.xmin), (self.ymax-self.ymin)
        self.xmin, self.xmax = x-wx/2.0, x+wx/2.0
        self.ymin, self.ymax = y-wy/2.0, y+wy/2.0

    def get_axes_zoom(self):
        (xmin, xmax), (ymin, ymax) = self.get_axes_limits()
        return float(xmax-xmin)/(self.xmax-self.xmin)

    @trigger_update
    def set_axes_zoom(self, z):
        z = min(max(z, 1.0), 25.0)
        (xmin, xmax), (ymin, ymax) = self.get_axes_limits()
        wx, wy = (xmax-xmin), (ymax-ymin)
        cx, cy = (self.xmax+self.xmin)/2.0, (self.ymax+self.ymin)/2.0
        self.xmin, self.xmax = cx-wx/2.0/z, cx+wx/2.0/z
        self.ymin, self.ymax = cy-wy/2.0/z, cy+wy/2.0/z

    def get_axis_limits(self, a):
        return self.get_bbox()[a]

    def get_axis_length(self, a):
        imin, imax = self.get_axis_limits(a)
        return imax - imin

    @trigger_update
    def set_proj(self, proj):
        self.proj = constrict(proj, self.get_bbox())

    @trigger_update
    def set_proj_axis(self, a, i):
        imin, imax = self.get_axis_limits(a)
        self.proj[a] = min(max(i, imin), imax-1)

    def get_display_str(self, point=False):
        s = ["%d" % a for a in self.proj]
        if not point:
            s[self.a1] = "[%d-%d]" % (self.xmin, self.xmax)
            s[self.a2] = "[%d-%d]" % (self.ymin, self.ymax)
        return "x".join(s)

    def updated(self): pass

# Plotting front end component: interfaces the matplotlib axes to perform required actions
class AxesAdapter(Projection):

    @trigger_update
    def __init__(self, figure_adapter, axes_ind, space_key):
        Projection.__init__(self)
        self.figure_adapter = figure_adapter
        self.space_key = space_key
        self.axes_ind = axes_ind
        self.plot_objects = [Crosshair(self), AxesIndicator(self), SpaceIndicator(self)]
        if self.space_key:
            self.reset_limits()
            self.reset_point()

    def get_ax(self):
        return self.figure_adapter.gui.plotter.figure.axes[self.axes_ind]

    def get_space(self):
        return self.figure_adapter.gui.model.spaces.get_space(self.space_key)

    def updated(self):
        ax = self.get_ax()
        del ax.patches[:]
        del ax.images[:]
        if self.space_key:
            space = self.get_space()
            for z, array in enumerate(space.arrays):
                if array.contains(self.proj, skip=(self.a1, self.a2)):
                    if isinstance(array, Data.AbstractROI):
                        ax.add_patch(array.get_patch(self.proj, self.a1, self.a2))
                    elif isinstance(array, Data.DataArray):
                        xlims, ylims = array.bbox[self.a1], array.bbox[self.a2]
                        array_data = array.get_slice(self.proj, to=(self.a1, self.a2))
                        ax.imshow(array_data, extent=xlims+ylims, origin='lower', interpolation='nearest',
                                  cmap=array.cmap, vmin=array.vmin, vmax=array.vmax, alpha=array.alpha)
        ax.set_xlim((self.xmin, self.xmax))
        ax.set_ylim((self.ymin, self.ymax))
        ax.set_aspect(self.get_axes_aspect())
        [obj.update() for obj in self.plot_objects]
        self.figure_adapter.redraw_canvas()


# Plot object: produces a certain artifact to a given axes based on adapter properties
class PlotObject(object):
    def update(self): pass
    def delete(self): pass

class Crosshair(PlotObject):

    def __init__(self, adapter):
        self.adapter = adapter
        self.l1 = Line2D((0,0),(0,0), color='green', visible=False)
        self.l2 = Line2D((0,0),(0,0), color='green', visible=False)
        self.adapter.get_ax().lines.extend((self.l1,self.l2))

    def update(self):
        x1, x2 = self.adapter.xmin, self.adapter.xmax
        y1, y2 = self.adapter.ymin, self.adapter.ymax
        x,y = self.adapter.get_axes_point()
        trans = self.adapter.get_ax().transData
        self.l1.set(xdata=[x, x], ydata=[y1, y2], transform=trans, visible=(x >= x1 and x <= x2))
        self.l2.set(xdata=[x1, x2], ydata=[y, y], transform=trans, visible=(y >= y1 and y <= y2))

    def delete(self):
        ax = self.adapter.get_ax()
        ax.axes.lines.remove(self.l1)
        ax.axes.lines.remove(self.l2)

class AxesIndicator(PlotObject):

    def __init__(self, adapter):
        self.adapter = adapter
        ax = self.adapter.get_ax()
        ax.grid('on')
        matplotlib.artist.setp(ax.get_xticklabels(), fontsize='6')
        matplotlib.artist.setp(ax.get_yticklabels(), fontsize='6')

    def update(self):
        ax = self.adapter.get_ax()
        x,y = self.adapter.get_axes_labels()
        ax.set_xlabel(x, size='small')
        ax.set_ylabel(y, size='small')

    def delete(self): pass

class SpaceIndicator(PlotObject):

    def __init__(self, adapter):
        self.adapter = adapter
        ax = self.adapter.get_ax()
        self.txt = ax.text(0.05, 0.95, "", fontsize=10, color='red', fontweight='bold', va='top',
                           transform=ax.transAxes)

    def update(self):
        ax = self.adapter.get_ax()
        if self.adapter.space_key:
            ax.set_axis_bgcolor('white')
            self.txt.set(text=self.adapter.space_key)
        else:
            ax.set_axis_bgcolor('black')
            self.txt.set(text="None")

    def delete(self):
        self.adapter.get_ax().texts.remove(self.txt)