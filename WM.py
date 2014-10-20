
import numpy
import matplotlib

#TODO: This can be made a lot simpler, do it when it works
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

image_kwargs = dict(interpolation='nearest')

class T :
    N = 4
    ACTIVE = 0
    SOURCE = 1
    NORM = 2
    SLICE = 3


# TODO: Add explicit erros for faulty calls and structures, these can be hard to debug otherwise
class WM_instance(object):

    def __init__(self, template_name, template, sources, all_sources, fig=None):

        if fig == None:
            self.fig = matplotlib.figure.Figure(figsize=(5,4), dpi=100)
        else:
            fig.clear()
            self.fig = fig

        self.all_sources = all_sources
        self.sources = numpy.array(sources)
        self.template_name = template_name

        grid_size = template.shape[0] * template.shape[1]

        n_sources = len(sources)
        n_template_sources = numpy.unique(template[:,:,T.SOURCE]).size

        #self.sources = numpy.array([None]*n_sources)
        self.views = numpy.array((),dtype=object)
        self.axes = numpy.array((),dtype=object)
        # X is a matrix that determines which views a source controls
        self.X_source_view = numpy.zeros((n_sources,grid_size), dtype=bool)
        self.axes_to_axes_adapter = dict()

        self.set_template(template)


    def change_template(self, new_template_name, action_axis):
        print "changing to", new_template_name
        action_view = self.get_view(action_axis)
        template, sources = transition(self.sources, self.template_name, new_template_name,
                                       self.view_to_source_ind(action_view),
                                       action_view)
        self.__init__(new_template_name, template, sources, self.all_sources, self.fig)

    def set_template(self, template):
        rows, cols, props = template.shape
        t = rows*cols
        for i in range(t):
            x, y = i/cols, i%cols
            if template[x,y,T.ACTIVE]:
                source_ind = template[x, y, T.SOURCE]
                norm_ind = template[x, y, T.NORM]
                slice_ind = template[x, y, T.SLICE]
                print "Adding grid item", x,y, "with norm",  norm_ind, "and source", self.sources[source_ind]
                ax = self.fig.add_subplot(rows,cols,i+1)
                view = View(norm_ind, slice_ind, 0)
                view.read_source_properties(self.sources[source_ind])
                self.add_connection(ax,view,source_ind)
                ax2 = AxesAdapter(ax, view, self)
                self.axes_to_axes_adapter[ax] = ax2
                ax2.reset_image()

    def add_connection(self, axis, view, source_ind):
        self.axes = numpy.append(self.axes,axis)
        self.views = numpy.append(self.views,view)
        self.X_source_view[source_ind,self.view_to_ind(view)] = True
        #print self.X_source_view


    # These stupid helpers allow changing the underlying datatype later

    def ind_to_view(self, ind):
        return self.views[ind]

    def view_to_ind(self, view):
        return numpy.nonzero(self.views==view)[0][0]

    def ind_to_source(self, ind):
        return self.sources[ind]

    def view_to_source_ind(self, view):
        source_flag = self.X_source_view[:,self.view_to_ind(view)]
        return numpy.nonzero(source_flag==True)[0][0]

    def ind_to_axis(self, ind):
        return self.axes[ind]

    def axis_to_ind(self, axis):
        return numpy.nonzero(self.axes==axis)[0][0]

    def get_view(self, axis):
        return self.views[self.axis_to_ind(axis)]

    def get_axis(self, view):
        return self.axes[self.view_to_ind(view)]

    def get_source(self, view):
        source_flag = self.X_source_view[:,self.view_to_ind(view)]
        return self.sources[source_flag][0]

    def get_sources(self):
        return self.sources

    def get_adapter(self, axis):
        return self.axes_to_axes_adapter[axis]

    def change_views_source(self, view, new_source_index):
        view_index = self.view_to_ind(view)
        cur_source_index = self.view_to_source_ind(view)
        self.X_source_view[cur_source_index,view_index] = False
        self.X_source_view[new_source_index,view_index] = True
        view.read_source_properties(self.get_source(view))

    def change_source(self, source_index, new_source_from_index):
        views_flag = self.X_source_view[source_index,:]
        self.sources[source_index] = self.all_sources[new_source_from_index]
        for view in self.views[views_flag]:
            ax = self.axes[self.view_to_ind(view)]
            view.read_source_properties(self.get_source(view))
            self.axes_to_axes_adapter[ax].reset_image()

    def get_shared_axes(self, view):
        source_index = self.view_to_source_ind(view)
        axes = numpy.array((),dtype=object)
        views_flag = self.X_source_view[source_index,:]
        for shared_axis in self.axes[views_flag]:
            axes = numpy.append(axes, shared_axis)
        return axes

    def get_figure(self):
        return self.fig

    def print_debug(self):
        pass

class AxesAdapter(object):

    def __init__(self, ax, view, Winst):
        self.ax = ax
        self.view = view
        self.Winst = Winst

    def reset_image(self):
        a = self.ax
        view = self.view
        ind = self.Winst.view_to_source_ind(view)
        # Initialization
        a.clear()
        if self.has_image():
            a.imshow(self.get_data(), origin='lower', vmin = view.v_min, vmax = view.v_max, **image_kwargs)
            a.set_aspect(view.get_axes_aspect())
        else:
            a.text(0.5, 0.5, "No Image", transform=a.transAxes, fontsize=10, color='red', style='italic',
                   clip_box=(0.0,0.0,1.0,1.0), clip_on=True, va='center', ha='center')
        a.text(0.05, 0.95, ind, transform=a.transAxes, fontsize=14, color='green', fontweight='bold',
               va='top')
        a.set_xticks([])
        a.set_yticks([])
        x,y = view.get_axes_labels()
        a.set_xlabel(x)
        a.set_ylabel(y)
        # Source indication

    def update_image(self):
        if self.has_image():
            im = self.ax.get_images()[0]
            im.set_data(self.get_data())
            im.norm.vmin,im.norm.vmax = self.view.v_min, self.view.v_max

    def toggle_projection(self):
        self.view.toggle_projection()
        self.reset_image()


    def start_crosshair(self, start_x, start_y, event):
        pass

    def drag_crosshair(self, event):
        cur_x, cur_y = event.xdata, event.ydata
        point = self.get_point(cur_x, cur_y)

        for axis in self.Winst.get_shared_axes(self.view):
            a2 = self.Winst.get_adapter(axis)
            a2.draw_crosshair(point)
            a2.update_slice_from_point(point)
            a2.update_image()

    def end_crosshair(self):
        for axis in self.Winst.get_shared_axes(self.view):
            a2 = self.Winst.get_adapter(axis)
            a2.clear_crosshair()

    def get_point(self, cur_x, cur_y):
        shape = self.view.shape[:3]
        major = self.view.norm
        minor1, minor2 = MINOR_AXES_IND[major]

        x = min(max(cur_x, 0), shape[minor1])
        y = min(max(cur_y, 0), shape[minor2])
        point = [0,0,0]
        point[minor1] = x
        point[minor2] = y
        point[major] = self.view.get_slice()
        return point

    def draw_crosshair(self, point):

        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()
        major = self.view.norm
        minor1, minor2 = MINOR_AXES_IND[major]
        #print "drawing", self.view, "coord", point[minor1], point[minor2]
        #x1, y1, x2, y2 = 0,0,shape[minor1],shape[minor2]
        l1 = matplotlib.lines.Line2D([point[minor1], point[minor1]], [y1, y2], transform=self.ax.transData)
        l2 = matplotlib.lines.Line2D([x1, x2], [point[minor2], point[minor2]], transform=self.ax.transData)
        self.clear_crosshair()
        self.ax.lines.extend([l1,l2])

    def clear_crosshair(self):
        for line in self.ax.lines:
            del self.ax.lines[:]

    def update_slice_from_point(self, slice):
        self.view.set_slice(slice[self.view.norm])

    def start_pan(self, start_x, start_y, event_button):
        self._button_pressed = event_button
        self.ax.start_pan(start_x, start_y, event_button)

    def drag_pan(self, event):
        self.ax.drag_pan(self._button_pressed, event.key, event.x, event.y)

    def end_pan(self):
        self.ax.end_pan()
        self._button_pressed = None

    def start_slice(self, start_x, start_y, event):
        self.start_x = start_x
        self.start_y = start_y
        self.start_slice_n = self.view.get_slice()

    def drag_slice(self, event):
        cur_x, cur_y = event.x, event.y
        #moved = self.view.start_y - cur_y
        #rel = moved/10
        x1, y1, x2, y2 = self.ax.bbox.extents
        height = y2 - y1
        rel = (self.start_y - cur_y)/height
        slice = self.start_slice_n+rel*self.view.n_slices()
        self.view.set_slice(slice)
        self.update_image()

    def end_slice(self):
        self.start_x, self.start_y = 0,0
        self.start_slice_n = 0

    def start_bvalue(self, start_x, start_y, event):
        self.start_x = start_x
        self.start_y = start_y
        self.start_bvalue_n = self.view.get_bvalue()

    def drag_bvalue(self, event):
        cur_x, cur_y = event.x, event.y
        #moved = self.view.start_y - cur_y
        #rel = moved/10
        x1, y1, x2, y2 = self.ax.bbox.extents
        height = y2 - y1
        rel = (self.start_y - cur_y)/height
        bvalue = self.start_bvalue_n+rel*self.view.n_bvalues()
        self.view.set_bvalue(bvalue)
        self.update_image()

    def end_bvalue(self):
        self.start_x, self.start_y = 0,0
        self.start_bvalue_n = 0

    def change_projection(self, norm_ind):
        self.view.change_projection(norm_ind)
        self.reset_image()

    def change_source(self, ind):
        self.Winst.change_views_source(self.view,ind)
        self.reset_image()

    def get_data(self):
        return self.Winst.get_source(self.view).get_slice(self.view.norm,
                                                          self.view.slice, self.view.b_value)

    def has_image(self):
        return self.Winst.get_source(self.view) != None

    def get_display_str(self, cur_x, cur_y):
        d = tuple(self.get_point(cur_x, cur_y))+(self.view.get_bvalue(),)+tuple(self.get_shape())
        s = "%dx%dx%dx(%d)/%dx%dx%dx(%d)" % d
        return s

    def get_display_minor_str(self, cur_x, cur_y):
        shape = self.view.shape[:3]
        major = self.view.norm
        minor1, minor2 = MINOR_AXES_IND[major]

        s = ["","","",""]
        x1, x2 = self.ax.get_xlim()
        s[minor1] = "[%d-%d]x" % (x1,x2)
        x1, x2 = self.ax.get_ylim()
        s[minor2] = "[%d-%d]x" % (x1,x2)
        s[major] = "%dx"%int(self.view.get_slice())
        s[-1] = "(%d)"%int(self.view.get_bvalue())

        s = "".join(s)
        a = "/%dx%dx%dx(%d)" % tuple(self.get_shape())
        return s+a

    def get_shape(self):
        return self.view.shape

    def view_to_tuple(self):
        return (self.view.norm, self.view.slice, self.view.b_value)

    def view_from_tuple(self, t):
        self.view.__init__(*t)
        self.update_image()


class View(object):

    def __init__(self,  norm, slice, b_value):
        self.norm = norm
        self.slice = slice
        self.b_value = b_value

    def n_slices(self):
        return self.smax+1

    def n_bvalues(self):
        return self.bmax+1

    def set_slice(self, num):
        self.slice = min(max(num, self.smin), self.smax)

    def get_slice(self):
        return self.slice

    def set_bvalue(self, num):
        self.b_value = min(max(num, self.bmin), self.bmax)

    def get_bvalue(self):
        return self.b_value

    def change_projection(self,norm_i):
        self.norm = norm_i
        self.smax = self.shape[self.norm]-1
        self.set_slice(10)

    def toggle_projection(self):
        self.change_projection((self.norm+1)%3)

    def get_axes_labels(self):
        return (MINOR_AXES[self.norm][0], MINOR_AXES[self.norm][1])

    def get_axes_aspect(self):
        x_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][1]]
        y_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][0]]
        #return (y_mm_dim/x_mm_dim)
        return (x_mm_dim/y_mm_dim)
        #return 1.0

    def read_source_properties(self,source):
        if source != None:
            self.shape = source.get_shape()
            self.smin, self.smax = 0, self.shape[self.norm]-1
            self.bmin, self.bmax = 0, self.shape[-1]-1
            self.v_min, self.v_max = source.v_min(), source.v_max()
        else:
            self.shape = (0,)*4
            self.smin, self.smax = 0,0
            self.v_min, self.v_max = 0,0


class Image_source(object):

    """ Do not directly access attributes, I may add all sorts of cool hacks to getters/setters
    to speed image lookups"""

    def __init__(self, fn):
        self.fn = fn
        self.image = numpy.load(fn)
        self.shape = self.image.shape
        self.vmin = self.image.min()
        self.vmax = self.image.max()

    def __str__(self):
        return self.fn

    def get_shape(self):
        return self.shape

    def v_min(self):
        return self.vmin

    def v_max(self):
        return self.vmax

    def get_slice(self, slice_index, slice_value, b_value):
        d = 4
        x = [slice(None,None,None)]*d
        x[slice_index] = slice_value
        x[-1] = b_value
        # Image[:,...,:,slice_value,:,...,:,b_value]
        # slice_index --->
        return self.image[x].T

def template_sources(template):
    return numpy.unique(template[:,:,T.SOURCE]).size

TEMPLATES = {
    'FULLSCREEN' : numpy.array([
        [[1,0,0,0]]
    ]),
    'PROJECTION' : numpy.array([
        #[source, norm]
        [[1 ,0, 0, 0],
         [1, 0, 1, 0],
         [1, 0, 2, 0]]
    ]),
    'SLICES' : numpy.array([
        [[1,0]]
    ]),
    'COMPARE_FULLSCREEN' : numpy.array([
        [[1,0],
         [1,1]]
    ]),
    'COMPARE_PROJECTION' : numpy.array([
        [[1,0],
         [1,1]]
    ]),
}


#TODO: make this a table [from_template x to_template] filled with functions f_ij
#TODO: then transition does f_ij(action_view)
#TODO: if f_ij == None, this template is not defined.
#TODO:  and f_ij may be a composition of other functions,at the very least it is
#TODO:  a composition of source filtering and returning a static template...
#TODO:  many of these can be implemented functional programming style

def transition(old_sources, from_template, to_template, source_ind=None, view=None):

    transition_template = numpy.copy(TEMPLATES[to_template])
    transition_sources = numpy.copy(old_sources)

    # Make sure the input is valid
    n1, n2 = len(old_sources), template_sources(TEMPLATES[from_template])
    assert n1 == n2, "Got " + str(n1) + "sources, template (from) defines " + str(n2) + " sources."

    # If the number of current sources and new sources are different, filter sources
    n1, n2 = len(old_sources), template_sources(TEMPLATES[to_template])
    if n1 != n2:
        transition_sources, source_ind = filter_sources(transition_sources, source_ind, n1, n2)
        n1 = len(transition_sources) # has changed
        assert n1 == n2, "Template (to) defines " + str(n2) + "sources, filtered to " + str(n1) + " sources."
        assert source_ind < n1, "Source index" + str(source_ind) + "/0-" + str((n1-1)) + "invalid."

    undefined_error = "Transition from " + from_template + " to " + to_template + " not defined."
    has_click_source = (view != None and source_ind != None)

    if from_template == to_template:
        pass

    elif from_template == 'NONE':
        pass

    elif to_template == 'FULLSCREEN':
        if has_click_source:
            # T.ACTIVE, T.SOURCE, T.NORM, T.SLICE
            transition_template[0,0,:] = (1,source_ind,view.norm,view.slice)
        else:
            pass

    elif to_template == 'PROJECTION':
        #TODO: add the crosshair type knowledge here
        pass

    elif to_template == 'SLICES':
        if has_click_source:
            #TODO more precise maths
            n = view.n_slices()
            max_slices = 20
            jump = numpy.ceil(n/max_slices).astype(int)
            iter = max_slices-(max_slices%jump)
            gs = numpy.ceil(numpy.sqrt(iter)).astype(int)
            transition_template = numpy.zeros((gs,gs,T.N), dtype=int)
            for i in range(iter):
                x, y = i/gs, i%gs
                if i < n:
                    transition_template[x,y] = (1,source_ind,view.norm,i*jump)
                else:
                    transition_template[x,y] = (0,)*T.N
        else:
            raise RuntimeError, undefined_error

    elif to_template in ('COMPARE_PROJECTION', 'COMPARE_FULLSCREEN'):
        hack = to_template[8:]
        transition_template = numpy.copy(TEMPLATES[hack])
        for s in range(len(transition_sources)):
            transition_template[s,:,T.SOURCE] = s
            if source_ind != None:
                if s == source_ind:
                    if to_template == 'COMPARE_FULLSCREEN':
                        transition_template[s,:,:] = (1,source_ind,view.norm,view.slice)
                    if to_template == 'COMPARE_PROJECTION':
                        transition_template[s,view.norm,:] = (1,source_ind,view.norm,view.slice)
            if s != (len(transition_sources)-1):
                transition_template = numpy.vstack((transition_template,numpy.copy(TEMPLATES[hack])))

    elif from_template in ('COMPARE_PROJECTION', 'COMPARE_FULLSCREEN'):
        pass

    else:
        raise RuntimeError, undefined_error

    print transition_template, transition_sources
    return transition_template, transition_sources

def filter_sources(sources, clicked_source_ind, n_from, n_to):
    # If we need to add sources, append None as new sources
    if n_from < n_to:
        print "Appending sources..."
        for i in range(n_to-n_from):
            sources = numpy.append(sources, None)
        print sources
        return sources, clicked_source_ind
    # If we need to remove sources, cut from the end
    elif n_from > n_to:
        print "Removing sources..."
        cut_sources = sources[0:(n_from-n_to)]
        clicked_source = sources[clicked_source_ind]
        if clicked_source in cut_sources:
            sources = cut_sources
            print sources
            return sources, numpy.nonzero(sources==clicked_source)[0][0]
        # If the clicked source belongs to cut sources, put it in front and shift the rest
        else:
            new_sources = numpy.array([clicked_source],dtype=object)
            if (n_from-n_to-1) > 0 :
                new_sources = numpy.append(new_sources,sources[0:n_from-n_to-1])
            print new_sources
            return new_sources, 0
    else:
        pass