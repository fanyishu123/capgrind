
import numpy
import matplotlib
import os

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



class T :
    N = 4
    ACTIVE = 0
    SOURCE = 1
    NORM = 2
    SLICE = 3


# TODO: Add explicit erros for faulty calls and structures, these can be hard to debug otherwise
class WM_instance(object):

    def __init__(self, gui, template_name, template, sources, all_sources, fig=None):

        self.gui = gui

        if fig == None:
            self.fig = matplotlib.figure.Figure(figsize=(5,4), dpi=100)
        else:
            fig.clear()
            self.fig = fig

        self.all_sources = all_sources
        self.template_name = template_name

        grid_size = template.shape[0] * template.shape[1]

        n_sources = len(sources)
        n_template_sources = numpy.unique(template[:,:,T.SOURCE]).size

        #self.sources = numpy.array([None]*n_sources)
        #self.views = numpy.array((),dtype=object)

        self.sources = numpy.array(sources)
        self.axes = numpy.array((),dtype=object)
        self.adapters = numpy.array((),dtype=object)
        # X is a matrix that determines which views a source controls
        self.X_source_adapter = numpy.zeros((n_sources,grid_size), dtype=bool)

        self.set_template(template)


    def change_template(self, new_template_name, action_axis):
        print "changing to", new_template_name
        action_adapter = self.get_adapter(action_axis)
        template, sources = action_transition(self.sources, self.template_name, new_template_name,
                                       self.adapter_to_source_ind(action_adapter), action_adapter)
        self.__init__(self.gui, new_template_name, template, sources, self.all_sources, self.fig)
        self.gui.update_WM_menu()

    def change_template_multiple(self, new_template_name, n_new_sources, use_sources = None):
        use_sources = self.sources if (use_sources == None) else use_sources
        print "changing to", new_template_name, "with", n_new_sources, "sources"
        template, sources = transition(use_sources, self.template_name, new_template_name,
                                       n_new_sources)
        self.__init__(self.gui, new_template_name, template, sources, self.all_sources, self.fig)
        self.gui.update_WM_menu()

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
                source = self.sources[source_ind]
                ax = self.fig.add_subplot(rows,cols,i+1)
                ax2 = AxesAdapter(ax, self, (norm_ind, slice_ind, 0))
                #view = View(norm_ind, slice_ind, 0)
                #TODO: view.read_source_properties(self.sources[source_ind])
                self.add_connection(ax,ax2,source_ind)
                ax2.reset()


    def add_connection(self, axis, adapter, source_ind):
        self.axes = numpy.append(self.axes, axis)
        self.adapters = numpy.append(self.adapters, adapter)
        self.X_source_adapter[source_ind,self.adapter_to_ind(adapter)] = True


    def ind_to_axis(self, ind):
        return self.axes[ind]

    def axis_to_ind(self, axis):
        return numpy.nonzero(self.axes==axis)[0][0]

    def get_axis(self, adapter):
        return self.axes[self.adapter_to_ind(adapter)]


    def ind_to_adapter(self, ind):
        return self.adapters[ind]

    def adapter_to_ind(self, adapter):
        return numpy.nonzero(self.adapters==adapter)[0][0]

    def get_adapter(self, axis):
        return self.adapters[self.axis_to_ind(axis)]


    def ind_to_source(self, ind):
        return self.sources[ind]

    def source_to_ind(self, source):
        return numpy.nonzero(self.sources==source)[0][0]

    def get_source(self, adapter):
        source_flag = self.X_source_adapter[:,self.adapter_to_ind(adapter)]
        return self.sources[source_flag][0]

    def adapter_to_source_ind(self, adapter):
        source_flag = self.X_source_adapter[:,self.adapter_to_ind(adapter)]
        return numpy.nonzero(source_flag==True)[0][0]

    def get_sources(self):
        return self.sources


    def change_adapters_source(self, adapter, new_source_index):
        adapter_index = self.adapter_to_ind(adapter)
        cur_source_index = self.adapter_to_source_ind(adapter)
        self.X_source_adapter[cur_source_index,adapter_index] = False
        self.X_source_adapter[new_source_index,adapter_index] = True
        adapter.reset()

    def change_source(self, source_index, new_source_from_index):
        adapters_flag = self.X_source_adapter[source_index,:]
        self.sources[source_index] = self.all_sources[new_source_from_index]
        for adapter in self.adapters[adapters_flag]:
            adapter.reset()

    def get_shared_adapters(self, adapter):
        source_index = self.adapter_to_source_ind(adapter)
        adapters_flag = self.X_source_adapter[source_index,:]
        return self.adapters[adapters_flag]

    def get_adapters(self, source):
        source_index = self.source_to_ind(source)
        adapters_flag = self.X_source_adapter[source_index,:]
        return self.adapters[adapters_flag]


    def get_figure(self):
        return self.fig

    def print_debug(self):
        for ax2 in self.adapters:
            print "debug:"
            print ax2.ax.get_position()
            #print ax2.ax.get_position(True)



class View(object):

    def __init__(self,  norm, slice, b_value):
        self.norm = norm
        self.slice = slice
        self.b_value = b_value

    def n_slices(self):
        return self.smax+1

    def set_slice(self, num):
        self.slice = min(max(num, self.smin), self.smax)

    def n_bvalues(self):
        return self.bmax+1

    def set_bvalue(self, num):
        self.b_value = min(max(num, self.bmin), self.bmax)

    def change_projection(self,norm_i):
        self.norm = norm_i
        self.smax = self.shape[self.norm]-1
        self.slice = 10

    def toggle_projection(self):
        self.change_projection((self.norm+1)%3)

    def get_axes_labels(self):
        return (MINOR_AXES[self.norm][0], MINOR_AXES[self.norm][1])

    def get_axes_aspect(self):
        x_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][1]]
        y_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][0]]
        return (x_mm_dim/y_mm_dim)

    def update_source_properties(self,source):
        if source != None:
            self.shape = source.get_shape()
            self.smin, self.smax = 0, self.shape[self.norm]-1
            self.bmin, self.bmax = 0, self.shape[-1]-1
        else:
            self.shape = (0,)*4
            self.smin, self.smax = 0,0


class AxesAdapter(View):

    def __init__(self, ax, Winst, view_tuple, source = None):
        self.ax = ax
        self.Winst = Winst
        View.__init__(self, *view_tuple)
        self.update_source_properties(source)
        #super(AxesAdapter,self).__init__()

    def reset(self):
        self.update_source_properties(self.Winst.get_source(self))
        self.reset_image()


    def has_image(self):
        return self.Winst.get_source(self) != None

    def reset_image(self):
        a = self.ax
        ind = self.Winst.adapter_to_source_ind(self)
        a.clear()
        if self.has_image():
            kwargs = self.Winst.get_source(self).kwargs
            a.imshow(self.get_data(), origin='lower', **kwargs)
            a.set_aspect(self.get_axes_aspect())
        else:
            a.text(0.5, 0.5, "No Image", transform=a.transAxes, fontsize=10, color='red',style='italic',
                   clip_box=(0.0,0.0,1.0,1.0), clip_on=True, va='center', ha='center')
        a.text(0.05, 0.95, ind, transform=a.transAxes, fontsize=14, color='green', fontweight='bold',
               va='top')
        a.set_xticks([])
        a.set_yticks([])
        x,y = self.get_axes_labels()
        a.set_xlabel(x)
        a.set_ylabel(y)

    def update_image(self):
        if self.has_image():
            im = self.ax.get_images()[0]
            im.set_data(self.get_data())
            kwargs = self.Winst.get_source(self).kwargs
            im.norm.vmin,im.norm.vmax = kwargs['vmin'], kwargs['vmax']

    def get_data(self):
        return self.Winst.get_source(self).get_slice(self.norm,
                                                          self.slice, self.b_value)

    def get_shape(self):
        return self.shape

    def get_point(self, cur_x, cur_y):
        shape = self.shape[:3]
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]

        x = min(max(cur_x, 0), shape[minor1])
        y = min(max(cur_y, 0), shape[minor2])
        point = [0,0,0]
        point[minor1] = x
        point[minor2] = y
        point[major] = self.slice
        return point

    def update_slice_from_point(self, point):
        self.set_slice(point[self.norm])


    def start_crosshair(self, start_x, start_y, event):
        pass

    def drag_crosshair(self, event):
        cur_x, cur_y = event.xdata, event.ydata
        point = self.get_point(cur_x, cur_y)

        for a2 in self.Winst.get_shared_adapters(self):
            a2.draw_crosshair(point)
            a2.update_slice_from_point(point)
            a2.update_image()

    def end_crosshair(self):
        for a2 in self.Winst.get_shared_adapters(self):
            a2.clear_crosshair()

    def draw_crosshair(self, point):

        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()
        major = self.norm
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
        self.start_slice_n = self.slice

    def drag_slice(self, event):
        cur_x, cur_y = event.x, event.y
        #moved = self.view.start_y - cur_y
        #rel = moved/10
        x1, y1, x2, y2 = self.ax.bbox.extents
        height = y2 - y1
        rel = (self.start_y - cur_y)/height
        slice = self.start_slice_n+rel*self.n_slices()
        self.set_slice(slice)
        self.update_image()

    def end_slice(self):
        self.start_x, self.start_y = 0,0
        self.start_slice_n = 0


    def start_bvalue(self, start_x, start_y, event):
        self.start_x = start_x
        self.start_y = start_y
        self.start_bvalue_n = self.b_value

    def drag_bvalue(self, event):
        cur_x, cur_y = event.x, event.y
        #moved = self.view.start_y - cur_y
        #rel = moved/10
        x1, y1, x2, y2 = self.ax.bbox.extents
        height = y2 - y1
        rel = (self.start_y - cur_y)/height
        bvalue = self.start_bvalue_n+rel*self.n_bvalues()
        self.set_bvalue(bvalue)
        self.update_image()

    def end_bvalue(self):
        self.start_x, self.start_y = 0,0
        self.start_bvalue_n = 0


    def toggle_projection(self):
        super(AxesAdapter,self).toggle_projection()
        self.reset_image()

    def change_projection(self, norm_ind):
        super(AxesAdapter,self).change_projection(norm_ind)
        self.reset_image()

    def change_source(self, ind):
        self.Winst.change_adapters_source(self,ind)
        self.reset_image()


    def get_display_str(self, cur_x, cur_y):
        d = tuple(self.get_point(cur_x, cur_y))+(self.b_value,)+tuple(self.shape)
        s = "%dx%dx%dx(%d)/%dx%dx%dx(%d)" % d
        return s

    def get_display_minor_str(self, cur_x, cur_y):
        shape = self.shape[:3]
        major = self.norm
        minor1, minor2 = MINOR_AXES_IND[major]

        s = ["","","",""]
        x1, x2 = self.ax.get_xlim()
        s[minor1] = "[%d-%d]x" % (x1,x2)
        x1, x2 = self.ax.get_ylim()
        s[minor2] = "[%d-%d]x" % (x1,x2)
        s[major] = "%dx"%int(self.slice)
        s[-1] = "(%d)"%int(self.b_value)

        s = "".join(s)
        a = "/%dx%dx%dx(%d)" % tuple(self.shape)
        return s+a


    def view_to_tuple(self):
        return (self.norm, self.slice, self.b_value)

    def view_from_tuple(self, t):
        View.__init__(self, *t)
        self.update_image()



class Image_source(object):

    """ Do not directly access attributes, I may add all sorts of cool hacks to getters/setters
    to speed image lookups"""
    kws = {'interpolation' : {'Nearest' : 'nearest'},
         'cmap' : {'Greyscale' : 'gray', 'Jet' : 'jet', 'Blue monotone' : 'Blues_r'}}

    def __init__(self, fn):
        self.image = numpy.load(fn)
        self.fn = os.path.basename(fn)
        self.shape = self.image.shape
        self.vmin = self.image.min()
        self.vmax = self.image.max()
        self.kwargs = dict(interpolation='nearest', cmap='jet', vmin=self.vmin, vmax=self.vmax)

    def __str__(self):
        return self.fn

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
    ])
}

class UndefinedException(Exception):
    pass

#TODO: make this a table [from_template x to_template] filled with functions f_ij
#TODO: then transition does f_ij(action_view)
#TODO: if f_ij == None, this template is not defined.
#TODO:  and f_ij may be a composition of other functions,at the very least it is
#TODO:  a composition of source filtering and returning a static template...
#TODO:  many of these can be implemented functional programming style


def action_transition(old_sources, from_template, to_template, source_ind, adapter):

    transition_sources = single_out(old_sources, source_ind)

    undefined_error = "Transition from " + from_template + " to " + to_template + " not defined."
    transition_template = numpy.copy(TEMPLATES[to_template])
    if to_template == 'FULLSCREEN':
        transition_template[0,0,:] = (1,0,adapter.norm,adapter.slice)
    elif to_template == 'PROJECTION':
        #TODO: if cliked from crosshair, add the crosshair type knowledge here
        transition_template[0,adapter.norm,:] = (1,0,adapter.norm,adapter.slice)
    elif to_template == 'SLICES':

        n = adapter.n_slices()-1
        side = 4
        max_slices = side*side
        slice_inds = [float(n)/(max_slices-1)*i for i in range(max_slices)]
        slice_inds = numpy.round(slice_inds).astype(int)

        transition_template = numpy.zeros((side,side,T.N), dtype=int)
        for i,slice in enumerate(slice_inds):
            x, y = i/side, i%side
            transition_template[x,y] = (1,0,adapter.norm,slice)

    else:
        raise UndefinedException(undefined_error)

    print transition_template, transition_sources
    return transition_template, transition_sources


def transition(old_sources, from_template, to_template, to_n):

    transition_sources = numpy.copy(old_sources)
    transition_sources = filter_sources(transition_sources, len(old_sources), to_n)
    n = len(transition_sources) # should be equal to to_n

    undefined_error = "Transition from " + from_template + " to " + to_template + " not defined."
    transition_template = numpy.copy(TEMPLATES[to_template])
    if to_template in ('PROJECTION', 'FULLSCREEN'):
        for s in range(n):
            transition_template[s,:,T.SOURCE] = s
            if s != (len(transition_sources)-1):
                transition_template = numpy.vstack((transition_template,
                                                    numpy.copy(TEMPLATES[to_template])))
    else:
        raise UndefinedException(undefined_error)

    print transition_template, transition_sources
    return transition_template, transition_sources


def single_out(sources, source_ind):
    return numpy.array([sources[source_ind]])


def filter_sources(sources, n_from, n_to):
    # If we need to add sources, append None as new sources
    if n_from < n_to:
        print "Appending sources..."
        sources = numpy.append(sources, [None]*(n_to-n_from))
        print sources
        return sources
    # If we need to remove sources, cut from the end
    elif n_from > n_to:
        print "Removing sources..."
        has_image = numpy.array([],dtype=object)
        # Numpy doesn't overwrite comparison with None
        for source in sources:
            if source != None:
                has_image = numpy.append(has_image,source)
        if len(has_image) <= n_to:
            return numpy.append(has_image, [None]*(n_to-len(has_image)))
        else:
            return has_image[:n_to]
    else:
        return sources