#
#   Modified standard toolbar for image manipulation tasks and image WM awareness
#
#   Copied from:
#       matplotlib.backend_bases.NavigationToolbar2
#       matplotlib.backends.backend_tkagg.NavigationToolbar2TkAgg
#
#   If one can live with the dual function pan/zoom, it should be possible to subclass this.
#


import matplotlib
import matplotlib.cbook as cbook
from matplotlib.figure import Figure
from matplotlib.widgets import SubplotTool
import matplotlib.backends.windowing as windowing
from matplotlib.backends.backend_tkagg import ToolTip, FigureCanvasTkAgg, FigureManagerTkAgg

import numpy as np

import six
import Tkinter as Tk

import WM

import os.path
rcParams = matplotlib.rcParams

class Cursors:
    # this class is only used as a simple namespace
    HAND, POINTER, SELECT_REGION, MOVE = list(range(4))
cursors = Cursors()

cursord = {
    "none" : "arrow",
    "slice" : "fleur",
    "bvalue" : "fleur",
    "pan" : "hand2",
    "crosshair": "tcross",
    "ZOOM": "tcross",
    }

class NavigationToolbar2(object):
    """
    Base class for the navigation cursor, version 2

    backends must implement a canvas that handles connections for
    'button_press_event' and 'button_release_event'.  See
    :meth:`FigureCanvasBase.mpl_connect` for more information


    They must also define

      :meth:`save_figure`
         save the current figure

      :meth:`set_cursor`
         if you want the pointer icon to change

      :meth:`_init_toolbar`
         create your toolbar widget

      :meth:`draw_rubberband` (optional)
         draw the zoom to rect "rubberband" rectangle

      :meth:`press`  (optional)
         whenever a mouse button is pressed, you'll be notified with
         the event

      :meth:`release` (optional)
         whenever a mouse button is released, you'll be notified with
         the event

      :meth:`dynamic_update` (optional)
         dynamically update the window while navigating

      :meth:`set_message` (optional)
         display message

      :meth:`set_history_buttons` (optional)
         you can change the history back / forward buttons to
         indicate disabled / enabled state.

    That's it, we'll do the rest!
    """

    # list of toolitems to add to the toolbar, format is:
    # (
    #   text, # the text of the button (often not visible to users)
    #   tooltip_text, # the tooltip shown on hover (where possible)
    #   image_file, # name of the image for the button (without the extension)
    #   name_of_method, # name of the method in NavigationToolbar2 to call
    # )
    toolitems = (
        ('Sources', 'Select sources', 'move', 'wm_sources'),
        ('View', 'Select view', 'move', 'wm_view'),
        ('Source', 'Select source', 'move', 'source'),
        ('Axis', 'Toggle Axis', 'move', 'axis'),
        ('Crosshair', 'Show a point in space', 'move', 'crosshair'),
        ('B-value', 'Pan through b-values', 'move', 'bvalue'),
        ('Slice', 'Pan through slices', 'move', 'slice'),
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to  previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
        #('Debug', 'bind debug info here', 'filesave', 'debug'),
      )

    def __init__(self, canvas, Winst):
        self.canvas = canvas
        self.Winst = Winst
        canvas.toolbar = self
        # a dict from axes index to a list of view limits
        self._views = cbook.Stack()
        self._views2 = cbook.Stack()
        self._positions = cbook.Stack()  # stack of subplot positions


        self._idPress = None
        self._idRelease = None
        self._idDrag = self.canvas.mpl_connect(
            'motion_notify_event', self.mouse_move)
        self._ids_zoom = [] # Zoom equivalent for drag ID (mouse move, key press, key release)

        self._last_axis = None # Axis where the button was pressed
        self._xypress = None  # Press info for the zoom rectangle

        self._active = None # ID string denoting active mode
        self._button_pressed = None  # Save the mouse button pressed at canvas
        self._zoom_mode = None # Key pressed in zoom mode, to limit to y/x zooming

        self._lastCursor = None # GUI mouse cursor
        self.mode = '' # GUI status message
        self._init_toolbar()



  # a mode string for the status bar
        self.set_history_buttons()

    # ACTIVATION FUNCTIONS
    # General activation function called from the GUI
    def activate(self, mode_id, *args):
        """ General activation function for toolbar button press.
            Set the active mode and connect corresponding callbacks.
        """

        if self._active == mode_id:
            self._active = None
        else:
            self._active = mode_id
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''

        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''

        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event',
                                                    getattr(self, 'press_' + mode_id))
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                    getattr(self, 'release_' + mode_id))
            self.mode = mode_id
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self.set_message(self.mode)
    # just get rid of these altogether
    def pan(self, *args): self.activate('pan')
    def slice(self, *args): self.activate('slice')
    def crosshair(self, *args): self.activate('crosshair')
    def bvalue(self, *args): self.activate('bvalue')
    def axis(self, *args): self.activate('axis')
    def wm_sources(self, *args): self.activate('sources')
    def wm_view(self, *args): self.activate('view')
    def source(self, *args): self.activate('source')


    # CANVAS MOUSE PRESS
    # Called when mouse button is pressed
    def press(self, event): pass
    # General function to call when a mouse press occurs in canvas
    def press_canvas(self, mode_string, event, implements = (1,)):

        if event.button in implements:
            self._button_pressed = event.button
        else:
            self._button_pressed = None
            return

        # push the current view to define home if stack is empty
        if self._views.empty():
            self.push_current()

        x, y = event.x, event.y
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if x is not None and y is not None and a.in_axes(event) and a.get_navigate() and a.can_pan():

                self._last_axis = a
                self.canvas.mpl_disconnect(self._idDrag)
                # Can replaced by a subclass like structure
                a2 = self.Winst.get_adapter(a)
                if self._button_pressed == 1:
                    getattr(a2, 'start_'+self._active)(x, y, event.button)
                    self._idDrag = self.canvas.mpl_connect('motion_notify_event', getattr(self,'drag_'+self._active))
                elif self._button_pressed == 3:
                    #TODO: seperate zoom/pan into two buttons to get rid of the first if
                    if self._active == 'pan':
                        getattr(a2, 'start_'+self._active)(x, y, event.button)
                        self._idDrag = self.canvas.mpl_connect('motion_notify_event', getattr(self,'drag_'+self._active))
                    else:
                        getattr(self, self._active+'_menu')(event)


        self.press(event)
    # Connect to drag_mode
    def press_pan(self, event): self.press_canvas('pan', event, implements = (1,3))
    def press_slice(self, event): self.press_canvas('slice', event, implements = (1,))
    def press_crosshair(self, event): self.press_canvas('crosshair', event, implements = (1,))
    def press_bvalue(self, event): self.press_canvas('bvalue', event, implements = (1,))
    # Call mode_menu
    def press_axis(self, event): self.press_canvas('axis', event, implements = (3,))
    def press_sources(self, event): self.press_canvas('sources', event, implements = (3,))
    def press_view(self, event): self.press_canvas('view', event, implements = (3,))
    def press_source(self, event): self.press_canvas('source', event, implements = (3,))


    # CANVAS MOUSE DRAG
    # General function to call when a mouse drag occurs in canvas
    def drag_canvas(self, event):
        a = self._last_axis
        a2 = self.Winst.get_adapter(a)
        getattr(a2, 'drag_'+self._active)(event)
        self.display_message(event)
        self.dynamic_update()
    # When the tool is not active
    def mouse_move(self, event):
        if not event.inaxes or not self._active:
            if self._lastCursor != "none":
                self.set_cursor("none")
                self._lastCursor = "none"
        else:
            if self._lastCursor != self._active:
                if cursord.has_key(self._active):
                    self.set_cursor(self._active)
                else:
                    self.set_cursor("none")
                self._lastCursor = self._active
        self.display_message(event)

    def display_message(self, event):
        if event.inaxes and event.inaxes.get_navigate():
            try:
                a2 = self.Winst.get_adapter(event.inaxes)
                if self._active in ('crosshair', None):
                    s = a2.get_display_str(event.xdata, event.ydata)
                elif self._active in ('slice','bvalue','pan'):
                    s = a2.get_display_minor_str(event.xdata, event.ydata)
                else:
                    s = event.inaxes.format_coord(event.xdata, event.ydata)
            except (ValueError, OverflowError):
                pass
            else:
                if len(self.mode):
                    self.set_message('%s, %s' % (self.mode, s))
                else:
                    self.set_message(s)
        else:
            self.set_message(self.mode)


    # Drag functions
    def drag_pan(self, event): self.drag_canvas(event)
    def drag_slice(self, event): self.drag_canvas(event)
    def drag_bvalue(self, event): self.drag_canvas(event)
    def drag_crosshair(self, event): self.drag_canvas(event)
    # Menu functions, overwritten in GUI's subclass
    def axis_menu(self, event): pass
    def sources_menu(self, event): pass
    def view_menu(self, event): pass
    def source_menu(self, event): pass


    # CANVAS MOUSE RELEASE
    # Called when mouse button is released
    def release(self, event): pass
    # General function to call when a mouse release occurs in canvas
    def release_canvas(self, event):
        if self._button_pressed is None:
            return
        self.canvas.mpl_disconnect(self._idDrag)
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.mouse_move)

        if not self._last_axis:
            return
        a = self._last_axis
        a2 = self.Winst.get_adapter(a)
        # Menus do not implement this
        if hasattr(a2,'end_'+self._active):
            getattr(a2, 'end_'+self._active)()

        self._button_pressed = None
        self._last_axis = None

        self.push_current()
        self.release(event)
        self.draw()
    # just get rid of these altogether
    def release_pan(self, event): self.release_canvas(event)
    def release_slice(self, event): self.release_canvas(event)
    def release_crosshair(self, event): self.release_canvas(event)
    def release_bvalue(self, event): self.release_canvas(event)
    def release_axis(self, event): self.release_canvas(event)
    def release_sources(self, event): self.release_canvas(event)
    def release_view(self, event): self.release_canvas(event)
    def release_source(self, event): self.release_canvas(event)

    def get_method(self, a, f):
        if hasattr(a,f): return getattr(a, f)
        else:
            a2 = self.Winst.get_adapter(a)
            if hasattr(a2,f): return getattr(a2, f)
            else: return None

    # The black sheep
    def zoom(self, *args):
        """Activate zoom to rect mode"""
        if self._active == 'ZOOM':
            self._active = None
        else:
            self._active = 'ZOOM'

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''

        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''

        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event',
                                                    self.press_zoom)
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                      self.release_zoom)
            self.mode = 'zoom rect'
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self.set_message(self.mode)
    def press_zoom(self, event):
        """the press mouse button in zoom to rect mode callback"""
        # If we're already in the middle of a zoom, pressing another
        # button works to "cancel"
        if self._ids_zoom != []:
            for zoom_id in self._ids_zoom:
                self.canvas.mpl_disconnect(zoom_id)
            self.release(event)
            self.draw()
            self._xypress = None
            self._button_pressed = None
            self._ids_zoom = []
            return

        if event.button == 1:
            self._button_pressed = 1
        elif event.button == 3:
            self._button_pressed = 3
        else:
            self._button_pressed = None
            return

        x, y = event.x, event.y

        # push the current view to define home if stack is empty
        if self._views.empty():
            self.push_current()

        self._xypress = []
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if (x is not None and y is not None and a.in_axes(event) and
                    a.get_navigate() and a.can_zoom()):
                self._xypress.append((x, y, a, i, a.viewLim.frozen(),
                                      a.transData.frozen()))

        id1 = self.canvas.mpl_connect('motion_notify_event', self.drag_zoom)
        id2 = self.canvas.mpl_connect('key_press_event',
                                      self._switch_on_zoom_mode)
        id3 = self.canvas.mpl_connect('key_release_event',
                                      self._switch_off_zoom_mode)

        self._ids_zoom = id1, id2, id3
        self._zoom_mode = event.key

        self.press(event)
    def drag_zoom(self, event):
        """the drag callback in zoom mode"""

        if self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, lim, trans = self._xypress[0]

            # adjust x, last, y, last
            x1, y1, x2, y2 = a.bbox.extents
            x, lastx = max(min(x, lastx), x1), min(max(x, lastx), x2)
            y, lasty = max(min(y, lasty), y1), min(max(y, lasty), y2)

            if self._zoom_mode == "x":
                x1, y1, x2, y2 = a.bbox.extents
                y, lasty = y1, y2
            elif self._zoom_mode == "y":
                x1, y1, x2, y2 = a.bbox.extents
                x, lastx = x1, x2

            self.draw_rubberband(event, x, y, lastx, lasty)
    def release_zoom(self, event):
        """the release mouse button callback in zoom to rect mode"""
        for zoom_id in self._ids_zoom:
            self.canvas.mpl_disconnect(zoom_id)
        self._ids_zoom = []

        if not self._xypress:
            return

        last_a = []

        for cur_xypress in self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, lim, trans = cur_xypress
            # ignore singular clicks - 5 pixels is a threshold
            if abs(x - lastx) < 5 or abs(y - lasty) < 5:
                self._xypress = None
                self.release(event)
                self.draw()
                return

            x0, y0, x1, y1 = lim.extents

            # zoom to rect
            inverse = a.transData.inverted()
            lastx, lasty = inverse.transform_point((lastx, lasty))
            x, y = inverse.transform_point((x, y))
            Xmin, Xmax = a.get_xlim()
            Ymin, Ymax = a.get_ylim()

            # detect twinx,y axes and avoid double zooming
            twinx, twiny = False, False
            if last_a:
                for la in last_a:
                    if a.get_shared_x_axes().joined(a, la):
                        twinx = True
                    if a.get_shared_y_axes().joined(a, la):
                        twiny = True
            last_a.append(a)

            if twinx:
                x0, x1 = Xmin, Xmax
            else:
                if Xmin < Xmax:
                    if x < lastx:
                        x0, x1 = x, lastx
                    else:
                        x0, x1 = lastx, x
                    if x0 < Xmin:
                        x0 = Xmin
                    if x1 > Xmax:
                        x1 = Xmax
                else:
                    if x > lastx:
                        x0, x1 = x, lastx
                    else:
                        x0, x1 = lastx, x
                    if x0 > Xmin:
                        x0 = Xmin
                    if x1 < Xmax:
                        x1 = Xmax

            if twiny:
                y0, y1 = Ymin, Ymax
            else:
                if Ymin < Ymax:
                    if y < lasty:
                        y0, y1 = y, lasty
                    else:
                        y0, y1 = lasty, y
                    if y0 < Ymin:
                        y0 = Ymin
                    if y1 > Ymax:
                        y1 = Ymax
                else:
                    if y > lasty:
                        y0, y1 = y, lasty
                    else:
                        y0, y1 = lasty, y
                    if y0 > Ymin:
                        y0 = Ymin
                    if y1 < Ymax:
                        y1 = Ymax

            if self._button_pressed == 1:
                if self._zoom_mode == "x":
                    a.set_xlim((x0, x1))
                elif self._zoom_mode == "y":
                    a.set_ylim((y0, y1))
                else:
                    a.set_xlim((x0, x1))
                    a.set_ylim((y0, y1))
            elif self._button_pressed == 3:
                if a.get_xscale() == 'log':
                    alpha = np.log(Xmax / Xmin) / np.log(x1 / x0)
                    rx1 = pow(Xmin / x0, alpha) * Xmin
                    rx2 = pow(Xmax / x0, alpha) * Xmin
                else:
                    alpha = (Xmax - Xmin) / (x1 - x0)
                    rx1 = alpha * (Xmin - x0) + Xmin
                    rx2 = alpha * (Xmax - x0) + Xmin
                if a.get_yscale() == 'log':
                    alpha = np.log(Ymax / Ymin) / np.log(y1 / y0)
                    ry1 = pow(Ymin / y0, alpha) * Ymin
                    ry2 = pow(Ymax / y0, alpha) * Ymin
                else:
                    alpha = (Ymax - Ymin) / (y1 - y0)
                    ry1 = alpha * (Ymin - y0) + Ymin
                    ry2 = alpha * (Ymax - y0) + Ymin

                if self._zoom_mode == "x":
                    a.set_xlim((rx1, rx2))
                elif self._zoom_mode == "y":
                    a.set_ylim((ry1, ry2))
                else:
                    a.set_xlim((rx1, rx2))
                    a.set_ylim((ry1, ry2))

        self.draw()
        self._xypress = None
        self._button_pressed = None

        self._zoom_mode = None

        self.push_current()
        self.release(event)
    def _switch_on_zoom_mode(self, event):
        self._zoom_mode = event.key
        self.mouse_move(event)
    def _switch_off_zoom_mode(self, event):
        self._zoom_mode = None
        self.mouse_move(event)


    # GUI
    def _init_toolbar(self):
        """
        This is where you actually build the GUI widgets (called by
        __init__).  The icons ``home.xpm``, ``back.xpm``, ``forward.xpm``,
        ``hand.xpm``, ``zoom_to_rect.xpm`` and ``filesave.xpm`` are standard
        across backends (there are ppm versions in CVS also).

        You just need to set the callbacks

        home         : self.home
        back         : self.back
        forward      : self.forward
        hand         : self.pan
        zoom_to_rect : self.zoom
        filesave     : self.save_figure

        You only need to define the last one - the others are in the base
        class implementation.

        """
        raise NotImplementedError
    def set_message(self, s): pass
    def draw_rubberband(self, event, x0, y0, x1, y1): pass
    def save_figure(self, *args): raise NotImplementedError
    def set_cursor(self, cursor): pass
    def set_history_buttons(self): pass
    # Draw the canvas when idle
    def dynamic_update(self): pass


    # Undo/Redo
    def back(self, *args):
        """move back up the view lim stack"""
        self._views2.back()
        self._views.back()
        self._positions.back()
        self.set_history_buttons()
        self._update_view()
    def forward(self, *args):
        """Move forward in the view lim stack"""
        self._views2.forward()
        self._views.forward()
        self._positions.forward()
        self.set_history_buttons()
        self._update_view()
    def home(self, *args):
        """Restore the original view"""
        self._views2.home()
        self._views.home()
        self._positions.home()
        self.set_history_buttons()
        self._update_view()
    def push_current(self):
        """push the current view limits and position onto the stack"""
        vws = []
        lims = []
        pos = []
        for a in self.canvas.figure.get_axes():
            a2 = self.Winst.get_adapter(a)
            vws.append(a2.view_to_tuple())
            xmin, xmax = a.get_xlim()
            ymin, ymax = a.get_ylim()
            lims.append((xmin, xmax, ymin, ymax))
            # Store both the original and modified positions
            pos.append((
                a.get_position(True).frozen(),
                a.get_position().frozen()))
        self._views2.push(vws)
        self._views.push(lims)
        self._positions.push(pos)
        self.set_history_buttons()
    # Reset the stack
    def update(self):
        self._views2.clear()
        self._views.clear()
        self._positions.clear()
        self.set_history_buttons()
    # Set the view from current stack position
    def _update_view(self):
        wvs = self._views2()
        if wvs is None:
            return
        lims = self._views()
        if lims is None:
            return
        pos = self._positions()
        if pos is None:
            return
        for i, a in enumerate(self.canvas.figure.get_axes()):
            a2 = self.Winst.get_adapter(a)
            a2.view_from_tuple(wvs[i])
            xmin, xmax, ymin, ymax = lims[i]
            a.set_xlim((xmin, xmax))
            a.set_ylim((ymin, ymax))
            # Restore both the original and modified positions
            a.set_position(pos[i][0], 'original')
            a.set_position(pos[i][1], 'active')

        self.canvas.draw_idle()


    def debug(self, *args):
        self.Winst.print_debug()

    #TODO: in this case can just replace calls here with self.canvas.draw_idle()
    def draw(self):
        """Redraw the canvases, update the locators"""
        for a in self.canvas.figure.get_axes():
            xaxis = getattr(a, 'xaxis', None)
            yaxis = getattr(a, 'yaxis', None)
            locators = []
            if xaxis is not None:
                locators.append(xaxis.get_major_locator())
                locators.append(xaxis.get_minor_locator())
            if yaxis is not None:
                locators.append(yaxis.get_major_locator())
                locators.append(yaxis.get_minor_locator())

            for loc in locators:
                loc.refresh()
        self.canvas.draw_idle()




class NavigationToolbar2TkAgg(NavigationToolbar2, Tk.Frame):
    """
    Public attributes

      canvas   - the FigureCanvas  (gtk.DrawingArea)
      win   - the gtk.Window
    """
    def __init__(self, canvas, window, Winst):
        self.canvas = canvas
        self.window = window
        self._idle = True
        #Tk.Frame.__init__(self, master=self.canvas._tkcanvas)
        NavigationToolbar2.__init__(self, canvas, Winst)

    def destroy(self, *args):
        del self.message
        Tk.Frame.destroy(self, *args)

    def set_message(self, s):
        self.message.set(s)

    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        y0 =  height-y0
        y1 =  height-y1
        try: self.lastrect
        except AttributeError: pass
        else: self.canvas._tkcanvas.delete(self.lastrect)
        self.lastrect = self.canvas._tkcanvas.create_rectangle(x0, y0, x1, y1)

        #self.canvas.draw()

    def release(self, event):
        try: self.lastrect
        except AttributeError: pass
        else:
            self.canvas._tkcanvas.delete(self.lastrect)
            del self.lastrect

    def set_cursor(self, cursor):
        self.window.configure(cursor=cursord[cursor])
        #self.window.configure(cursor="tcross")

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
        Tk.Frame.__init__(self, master=self.window,
                          width=int(width), height=int(height),
                          borderwidth=2)

        self.update()  # Make axes menu

        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                # spacer, unhandled in Tk
                pass
            else:
                button = self._Button(text=text, file=image_file,
                                   command=getattr(self, callback))
                if tooltip_text is not None:
                    ToolTip.createToolTip(button, tooltip_text)

        self.message = Tk.StringVar(master=self)
        self._message_label = Tk.Label(master=self, textvariable=self.message)
        self._message_label.pack(side=Tk.RIGHT)
        self.pack(side=Tk.BOTTOM, fill=Tk.X)


    def configure_subplots(self):
        toolfig = Figure(figsize=(6,3))
        window = Tk.Tk()
        canvas = FigureCanvasTkAgg(toolfig, master=window)
        toolfig.subplots_adjust(top=0.9)
        tool =  SubplotTool(self.canvas.figure, toolfig)
        canvas.show()
        canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

    def save_figure(self, *args):
        import tkFileDialog
        import tkMessageBox
        filetypes = self.canvas.get_supported_filetypes().copy()
        default_filetype = self.canvas.get_default_filetype()

        # Tk doesn't provide a way to choose a default filetype,
        # so we just have to put it first
        default_filetype_name = filetypes[default_filetype]
        del filetypes[default_filetype]

        sorted_filetypes = list(six.iteritems(filetypes))
        sorted_filetypes.sort()
        sorted_filetypes.insert(0, (default_filetype, default_filetype_name))

        tk_filetypes = [
            (name, '*.%s' % ext) for (ext, name) in sorted_filetypes]

        # adding a default extension seems to break the
        # asksaveasfilename dialog when you choose various save types
        # from the dropdown.  Passing in the empty string seems to
        # work - JDH!
        #defaultextension = self.canvas.get_default_filetype()
        defaultextension = ''
        initialdir = rcParams.get('savefig.directory', '')
        initialdir = os.path.expanduser(initialdir)
        initialfile = self.canvas.get_default_filename()
        fname = tkFileDialog.asksaveasfilename(
            master=self.window,
            title='Save the figure',
            filetypes=tk_filetypes,
            defaultextension=defaultextension,
            initialdir=initialdir,
            initialfile=initialfile,
            )

        if fname == "" or fname == ():
            return
        else:
            if initialdir == '':
                # explicitly missing key or empty str signals to use cwd
                rcParams['savefig.directory'] = initialdir
            else:
                # save dir for next time
                rcParams['savefig.directory'] = os.path.dirname(six.text_type(fname))
            try:
                # This method will handle the delegation to the correct type
                self.canvas.print_figure(fname)
            except Exception as e:
                tkMessageBox.showerror("Error saving file", str(e))

    def set_active(self, ind):
        self._ind = ind
        self._active = [ self._axes[i] for i in self._ind ]

    def update(self):
        _focus = windowing.FocusManager()
        self._axes = self.canvas.figure.axes
        naxes = len(self._axes)
        #if not hasattr(self, "omenu"):
        #    self.set_active(range(naxes))
        #    self.omenu = AxisMenu(master=self, naxes=naxes)
        #else:
        #    self.omenu.adjust(naxes)
        NavigationToolbar2.update(self)

    def dynamic_update(self):
        'update drawing area only if idle'
        # legacy method; new method is canvas.draw_idle
        self.canvas.draw_idle()

    def axis_menu(self, event):
        """Show a popup menu to choose the axis"""
        pmenu = Tk.Menu(self)

        x = event.guiEvent.x_root
        y = event.guiEvent.y_root

        a = self._last_axis
        a2 = self.Winst.get_adapter(a)

        for i in range(3):
            axes_string = WM.MINOR_AXES[i][0]+WM.MINOR_AXES[i][1]
            # Calling the redraw is necessary *immediately*,
            # a bug with with internal state variables or event handling..?
            def f (i=i):
                a2.change_projection(i)
                self.dynamic_update()
            pmenu.add_command(label=axes_string, compound=Tk.LEFT, command=f)

        pmenu.tk_popup(int(x),int(y),0)

    def sources_menu(self, event):
        """Show a popup menu to choose the WM sources"""
        select_sources_menu = Tk.Menu(self)

        x = event.guiEvent.x_root
        y = event.guiEvent.y_root

        source_menu = []
        for i in range(len(self.Winst.sources)):
            source_menu.append(Tk.Menu(self, tearoff=0))
            select_sources_menu.add_cascade(label=str(i), menu=source_menu[-1])
            for j in range(len(self.Winst.all_sources)):
                def f (i=i,j=j):
                    self.Winst.change_source(i,j)
                    self.canvas.draw_idle()
                source_menu[-1].add_radiobutton(label=str(j)+" ("+str(self.Winst.all_sources[j])+")", command=f )

        select_sources_menu.tk_popup(int(x),int(y),0)

    def view_menu(self, event):
        """Show a popup menu to choose the WM view"""
        smenu = Tk.Menu(self)

        x = event.guiEvent.x_root
        y = event.guiEvent.y_root

        a = self._last_axis
        a2 = self.Winst.get_adapter(a)

        wm_views = WM.TEMPLATES.keys()
        for i,wm_view in zip(range(len(wm_views)),wm_views):
            def f (wm_view=wm_view,a=a):
                self.Winst.change_template(wm_view, a)
                self.canvas.draw()
            smenu.add_command(label=wm_view, compound=Tk.LEFT, command=f)

        smenu.tk_popup(int(x),int(y),0)

    def source_menu(self, event):
        """Show a popup menu to choose the view's image source"""
        smenu = Tk.Menu(self)

        x = event.guiEvent.x_root
        y = event.guiEvent.y_root

        a = self._last_axis
        a2 = self.Winst.get_adapter(a)

        sources = self.Winst.get_sources()
        for i,source in zip(range(len(sources)),sources):
            def f (i=i):
                a2.change_source(i)
                self.canvas.draw()
            smenu.add_command(label=str(i)+" ("+str(source)+")", compound=Tk.LEFT, command=f)

        smenu.tk_popup(int(x),int(y),0)


FigureCanvas = FigureCanvasTkAgg
FigureManager = FigureManagerTkAgg