#
#   Highly modified matplotlib toolbar for multidimensional array manipulation
#
#   Original source:
#       matplotlib.backend_bases.NavigationToolbar2
#       matplotlib.backends.backend_tkagg.NavigationToolbar2TkAgg
#

import os.path
import matplotlib
from matplotlib.backends.backend_tkagg import ToolTip #, FigureCanvasTkAgg, FigureManagerTkAgg
import Tkinter as Tk
import Tools

rcParams = matplotlib.rcParams

# General toolbar framework that interfaces with matplotlib canvas
class NavigationToolbar2(object):

    # Tool specification: (text, tooltip text, image file, cursor)
    toolitems = (
        Tools.Crosshair('Crosshair', 'Sync views to point', 'move', 'tcross'),
        Tools.BValue('B-value', 'Pan through b-values', 'move', 'double_arrow'),
        Tools.Zoom('Zoom', 'Zoom the axes', 'move', 'sizing'),
        Tools.Pan('Move', 'Move the axes', 'move', 'hand2'),
        Tools.ChangeAxes('Projection', 'Change projection into axes', 'move', 'll_angle'),
        Tools.ChangeSpace('Space', 'Change views space', 'move', 'icon'),
        Tools.HyperRectangleSelector('Hyperrectangle', 'Select hyperrectangle ROI', 'move', 'cross'),
        Tools.HyperEllipseSelector('Hyperrellipse', 'Select hyperellipse ROI', 'move', 'cross'),
      )

    def __init__(self, canvas):
        self.canvas = canvas
        canvas.toolbar = self

        self._idPress = None
        self._idScroll = None
        self._idRelease = None
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.mouse_move)

        self._last_axis = None  # Axis where the button was pressed
        self._lastCursor = None  # Previous mouse cursor
        self._active_tool = None  # Active tool object

        self.mode_str = '' # GUI status message
        self._init_toolbar()

    # ACTIVATION FUNCTIONS
    # General activation function called from the GUI
    def activate(self, tool):
        """ General activation function for toolbar button press.
            Set the active mode and connect corresponding callbacks.
        """
        self._active_tool = None if self._active_tool == tool else tool
        self.mode_str = '' if not self._active_tool else tool.name

        if self._idPress is not None: self._idPress = self.canvas.mpl_disconnect(self._idPress)
        if self._idScroll is not None: self._idScroll = self.canvas.mpl_disconnect(self._idScroll)
        if self._idRelease is not None: self._idRelease = self.canvas.mpl_disconnect(self._idRelease)

        # TODO: is there a deep reason to always rebind press? We could bind it just once and check _active_tool
        # TODO: in press_canvas. Check that permanent bind does not register on Tkinter widgets
        # TODO: if we do this, we can permabind drag as well my merging mouse_move to drag and adding state variable
        if self._active_tool:
            self._idPress = self.canvas.mpl_connect('button_press_event', getattr(self, 'press_canvas'))
            self._idScroll = self.canvas.mpl_connect('scroll_event', getattr(self, 'scroll_canvas'))
            self._idRelease = self.canvas.mpl_connect('button_release_event', getattr(self, 'release_canvas'))
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        self.set_message(self.mode_str)

    # CANVAS MOUSE PRESS
    # General function to call when a mouse press occurs in canvas
    def press_canvas(self, event):
        x, y = event.xdata, event.ydata
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if x is not None and y is not None and a.in_axes(event):
                self._last_axis = a
                a2 = self.get_adapter(a)
                if event.button == 1:
                    self.canvas.draw_idle()
                    self.canvas.mpl_disconnect(self._idDrag)
                    self._idDrag = self.canvas.mpl_connect('motion_notify_event', getattr(self,'drag_canvas'))
                    self._active_tool.start(a2, event)
                elif event.button == 3:
                    self._active_tool.menu(event, a2)

    # CANVAS MOUSE DRAG
    # General function to call when a mouse drag occurs in canvas
    def drag_canvas(self, event):
        a2 = self.get_adapter(self._last_axis)
        self._active_tool.drag(a2, event)
        self.display_message(event)
        self.canvas.draw_idle()

    # CANVAS MOUSE RELEASE
    # General function to call when a mouse release occurs in canvas
    def release_canvas(self, event):
        self.canvas.mpl_disconnect(self._idDrag)
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        if not self._last_axis: return
        a2 = self.get_adapter(self._last_axis)
        self._active_tool.end(a2, event)
        self._last_axis = None

    # CANVAS MOUSE SCROLL
    # General function to call when a mouse scroll occurs in canvas
    def scroll_canvas(self, event):
        x, y = event.xdata, event.ydata
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if x is not None and y is not None and a.in_axes(event):
                self._last_axis = a
                a2 = self.get_adapter(a)
                if event.button == 'up':
                    self._active_tool.scroll_up(a2, event)
                elif event.button == 'down':
                    self._active_tool.scroll_down(a2, event)
        self.display_message(event)
        self.canvas.draw_idle()

    # When a tool is not active
    def mouse_move(self, event):
        if not event.inaxes or not self._active_tool:
            if self._lastCursor != "arrow":
                self.set_cursor("arrow")
                self._lastCursor = "arrow"
        else:
            if self._lastCursor != self._active_tool.cursor:
                self.set_cursor(self._active_tool.cursor)
                self._lastCursor = self._active_tool.cursor
        self.display_message(event)

    def display_message(self, event):
        if event.inaxes and event.inaxes.get_navigate() and self._active_tool:
            a2 = self.get_adapter(event.inaxes)
            if self._active_tool.name == 'Crosshair':
                s = a2.get_display_str(point=True)
            else:
                s = a2.get_display_str()
            self.set_message(s)
        else:
            self.set_message(self.mode_str)

    # GUI
    def _init_toolbar(self):
        raise NotImplementedError

    def set_message(self, s): pass
    def set_cursor(self, cursor): pass

    def get_adapter(self, a):
        return self.gui.model.figure_adapter.adapters[self.canvas.figure.axes.index(a)]


# Tkinter specific toolbar logic
class NavigationToolbar2TkAgg(NavigationToolbar2, Tk.Frame):

    def __init__(self, canvas, gui, root):
        self.canvas = canvas
        self.gui = gui
        self.root = root
        self._idle = True
        #TODO: maybe we should merge these, calling the second 'init'/_init_toolbar back here is confusing
        NavigationToolbar2.__init__(self, canvas)

    def destroy(self, *args):
        del self.message
        Tk.Frame.destroy(self, *args)

    def set_message(self, s):
        self.message.set(s)

    def set_cursor(self, cursor):
        self.root.configure(cursor=cursor)

    def _Button(self, text, file, command, extension='.ppm'):
        img_file = os.path.join(rcParams['datapath'], 'images', file + extension)
        im = Tk.PhotoImage(master=self, file=img_file)
        b = Tk.Button(
            master=self, text=text, padx=2, pady=2, image=im, command=command)
        b._ntimage = im
        b.pack(side=Tk.LEFT)
        return b

    def _init_toolbar(self):
        xmin, xmax = self.canvas.figure.bbox.intervalx
        height, width = 50, xmax-xmin
        Tk.Frame.__init__(self, master=self.root, width=int(width), height=int(height), borderwidth=2)

        self.message = Tk.StringVar(master=self)
        self._message_label = Tk.Label(master=self, textvariable=self.message)
        self._message_label.pack(side=Tk.TOP, fill=Tk.X, expand=Tk.NO)

        for tool in self.toolitems:
            button = self._Button(text=tool.name, file=tool.icon,
                                  command=lambda tool=tool: getattr(self, 'activate')(tool))
            if tool.description is not None:
                ToolTip.createToolTip(button, tool.description)

        self.pack(side=Tk.BOTTOM, fill=Tk.X, expand=Tk.NO)
