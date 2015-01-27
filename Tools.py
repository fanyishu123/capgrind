#
#   Tools embedded in the toolbar to perform a requested action for a chosen adapter
#

from Globals import AXES, NORM_3D

import Tkinter as Tk

from Templates import STATIC_TEMPLATES, DYNAMIC_TEMPLATES
import Data


def get_rel(start_y, cur_y, min_y, max_y):
    return (start_y - cur_y)/(max_y - min_y)

#TODO: how can the superclass decorate overwritten methods in the subclass?
#TODO: some menus need to only react on adapters, some to the whole figure
#TODO: some actions are not defined when the view is unbinded, add error handling

class Tool(object):
    def __init__(self, name, description, icon, cursor='arrow'):
        self.name = name
        self.description = description
        self.icon = icon
        self.cursor = cursor
    def start(self, adapter, event): pass
    def drag(self, adapter, event): pass
    def end(self, adapter, event): pass
    def scroll_up(self, adapter, event): pass
    def scroll_down(self, adapter, event): pass
    def menu(self, event, adapter): pass

class GlobalTool(Tool):
    def __init__(self, name, description, icon, cursor='arrow'):
        super(GlobalTool, self).__init__(name, description, icon, cursor)
        self.g_action = True
    def menu(self, event, adapter):
        smenu = Tk.Menu(tearoff=0)
        def f(self=self): self.g_action = not self.g_action
        smenu.add_command(label="Local" if self.g_action else "[Local]", compound=Tk.LEFT, command=f)
        smenu.add_command(label="[Global]" if self.g_action else "Global", compound=Tk.LEFT, command=f)
        smenu.tk_popup(int(event.guiEvent.x_root),int(event.guiEvent.y_root),0)
#    def _propagate(self, adapter):
#        for a2 in adapter.fig_adapter.iter_space(adapter): a2.reset()

class Crosshair(Tool):

    def start(self, adapter, event):
        self.drag(adapter, event)

    def drag(self, adapter, event):
        adapter.set_axes_point(event.xdata, event.ydata)
        self._propagate(adapter)

    def scroll_up(self, adapter, event):
        a = NORM_3D[(adapter.a1, adapter.a2)]
        adapter.set_proj_axis(a, adapter.proj[a]+1)
        self._propagate(adapter)

    def scroll_down(self, adapter, event):
        a = NORM_3D[(adapter.a1, adapter.a2)]
        adapter.set_proj_axis(a, adapter.proj[a]-1)
        self._propagate(adapter)

    def _propagate(self, adapter):
        for a2 in adapter.figure_adapter.iter_space(adapter):
            a2.set_proj(adapter.proj)

    def menu(self, event, adapter):
        smenu = Tk.Menu(tearoff=0)
        for name in DYNAMIC_TEMPLATES.keys():
            smenu.add_command(label=name, compound=Tk.LEFT, command=lambda \
                    adapter=adapter,name=name: adapter.figure_adapter.set_template(name, adapter))
        smenu.tk_popup(int(event.guiEvent.x_root),int(event.guiEvent.y_root),0)

class Projection(object):

    def start_proj(self, adapter, event, a):
        self._start_i = adapter.proj[a]
        self._start_y = event.y

    def drag_proj(self, adapter, event, a):
        x1, y1, x2, y2 = adapter.get_ax().bbox.extents
        rel = get_rel(self._start_y, event.y, y1, y2)
        adapter.set_proj_axis(a, self._start_i+rel*adapter.get_axis_length(a))

    def end_proj(self, adapter, event, a): pass

    def inc_proj(self, adapter, event, a):
        adapter.set_proj_axis(a, adapter.proj[a]+1)

    def dec_proj(self, adapter, event, a):
        adapter.set_proj_axis(a, adapter.proj[a]-1)

class BValue(GlobalTool, Projection):

    def start(self, adapter, event):
        self.start_proj(adapter, event, -1)

    def drag(self, adapter, event):
        self.drag_proj(adapter, event, -1)
        if self.g_action: self._propagate(adapter)

    def end(self, adapter, event):
        self.end_proj(adapter, event, -1)

    def scroll_up(self, adapter, event):
        self.inc_proj(adapter, event, -1)
        if self.g_action: self._propagate(adapter)

    def scroll_down(self, adapter, event):
        self.dec_proj(adapter, event, -1)
        if self.g_action: self._propagate(adapter)

    def _propagate(self, adapter):
        for a2 in adapter.figure_adapter.iter_space(adapter):
            a2.set_proj(adapter.proj)

class Zoom(GlobalTool):

    def start(self, adapter, event):
        self._start_y = event.y
        self._start_z = adapter.get_axes_zoom()

    def drag(self, adapter, event):
        x1, y1, x2, y2 = adapter.get_ax().bbox.extents
        rel = get_rel(self._start_y, event.y, y1, y2)
        adapter.set_axes_zoom(self._start_z+rel*10.0)
        if self.g_action: self._propagate(adapter)

    def end(self, adapter, event): pass

    def scroll_up(self, adapter, event):
        adapter.set_axes_zoom(adapter.get_axes_zoom()*2.0)
        if self.g_action: self._propagate(adapter)

    def scroll_down(self, adapter, event):
        adapter.set_axes_zoom(adapter.get_axes_zoom()*0.5)
        if self.g_action: self._propagate(adapter)

    def _propagate(self, adapter):
        z = adapter.get_axes_zoom()
        for a2 in adapter.figure_adapter.iter_space(adapter):
            a2.set_axes_zoom(z)

class Pan(Tool):

    def start(self, adapter, event):
        self._start_x = event.x
        self._start_y = event.y
        self._start_xmin = adapter.xmin
        self._start_ymin = adapter.ymin

    def drag(self, adapter, event):
        x1, y1, x2, y2 = adapter.get_ax().bbox.extents
        xrel, yrel = get_rel(self._start_x, event.x, x1, x2), get_rel(self._start_y, event.y, y1, y2)
        wx, wy = (adapter.xmax-adapter.xmin), (adapter.ymax-adapter.ymin)
        nx, ny = self._start_xmin + xrel*wx, self._start_ymin + yrel*wy
        adapter.set_axes_limits(((nx, nx+wx), (ny, ny+wy)))

    def end(self, adapter, event): pass

class ChangeAxes(Tool):

    def start(self, adapter, event):
        minors = NORM_3D.keys()
        a1, a2 = minors[(minors.index((adapter.a1, adapter.a2)) + 1) % len(minors)]
        adapter.set_axes(a1, a2)

    def drag(self, adapter, event): pass

    def end(self, adapter, event): pass

    def menu(self, event, adapter):
        smenu = Tk.Menu(tearoff=0)
        for t, a in NORM_3D.items():
            smenu.add_command(label=AXES[a], compound=Tk.LEFT, command=\
                lambda a1=t[0],a2=t[1],adapter=adapter: adapter.set_axes(a1, a2))
        smenu.tk_popup(int(event.guiEvent.x_root),int(event.guiEvent.y_root),0)

class ChangeSpace(Tool):

    def menu(self, event, adapter):
        smenu = Tk.Menu(tearoff=0)
        for space_ind, space in enumerate(adapter.figure_adapter.gui.model.spaces.spaces):
            smenu.add_command(label=str(space), compound=Tk.LEFT, command=\
                lambda adapter=adapter,space=space: adapter.set_space(space.key))
        smenu.tk_popup(int(event.guiEvent.x_root),int(event.guiEvent.y_root),0)


# TODO: fix space addition and referring to actual space object
class ROISelector(GlobalTool):
    def __init__(self, name, description, icon, cursor='arrow'):
        super(ROISelector, self).__init__(name, description, icon, cursor)
        self._last_space = None
        self.roi = None
        self.ROI_OBJ = None

    def start(self, adapter, event):
        self._start_x, self._start_y = event.xdata, event.ydata
        if not self.roi or self._last_space != adapter.space_key:
            roi = self.ROI_OBJ()
            adapter.get_space().add_array(roi)
            self._last_space = adapter.space_key
            self.roi = roi
        self._set_roi_start(adapter)

    def _set_roi_start(self, adapter):
        c = [p for p in adapter.proj]
        c[adapter.a1] = self._start_x
        c[adapter.a2] = self._start_y
        self.roi.set_roi_axes(c, [0 for p in adapter.proj])

    def drag(self, adapter, event):
        if event.xdata and event.ydata:
            dx = abs(self._start_x - event.xdata)
            dy = abs(self._start_y - event.ydata)
            self.roi.update_roi_axes_r(adapter.a1, dx)
            self.roi.update_roi_axes_r(adapter.a2, dy)
            #self._propagate(adapter)

    def scroll_up(self, adapter, event):
        if self.roi:
            a = NORM_3D[(adapter.a1, adapter.a2)]
            self.roi.update_roi_axes_r(a, self.roi.get_roi_axes_r(a)+1)
            #self._propagate(adapter)

    def scroll_down(self, adapter, event):
        if self.roi:
            a = NORM_3D[(adapter.a1, adapter.a2)]
            if self.roi.get_roi_axes_r(a) >= 1:
                self.roi.update_roi_axes_r(a, self.roi.get_roi_axes_r(a)-1)
                #self._propagate(adapter)

    def menu(self, event, adapter):
        ROIs = [array for array in adapter.get_space().arrays if isinstance(array, self.ROI_OBJ)]
        smenu = Tk.Menu(tearoff=0)
        for roi in ROIs:
            txt = str(roi) if roi != self.roi else "[" + str(roi) + "]"
            smenu.add_command(label=txt, compound=Tk.LEFT, command=lambda self=self,space=adapter.get_space(),roi=roi:\
                self._set_roi(space, roi))
        smenu.tk_popup(int(event.guiEvent.x_root),int(event.guiEvent.y_root),0)

    def _set_roi(self, space, roi):
        self._last_space = space
        self.roi = roi

class HyperRectangleSelector(ROISelector):
    def __init__(self, name, description, icon, cursor='arrow'):
        super(HyperRectangleSelector, self).__init__(name, description, icon, cursor)
        self.ROI_OBJ = Data.HyperRectangleROI

class HyperEllipseSelector(ROISelector):
    def __init__(self, name, description, icon, cursor='arrow'):
        super(HyperEllipseSelector, self).__init__(name, description, icon, cursor)
        self.ROI_OBJ = Data.HyperEllipseROI

