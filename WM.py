
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
    'SLICES' : numpy.array([[[]]]),
    'COMPARE_FULLSCREEN' : numpy.array([[[]]]),
    'COMPARE_PROJECTION' : numpy.array([[[]]]),
}

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
        n_sources = numpy.unique(template[:,:,1]).size

        #self.sources = numpy.array([None]*n_sources)
        self.views = numpy.array((),dtype=object)
        self.axes = numpy.array((),dtype=object)
        # X is a matrix that determines which views a source controls
        self.X_source_view = numpy.zeros((len(sources),grid_size), dtype=bool)
        self.axes_to_axes_adapter = dict()

        self.set_template(template)


    def change_template(self, new_template_name, action_axis):
        print "changing to", new_template_name
        template, sources = transition(self, action_axis, self.template_name, new_template_name)
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
            a.imshow(self.get_data(), vmin = view.v_min, vmax = view.v_max, **image_kwargs)
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

    def start_slice(self, start_x, start_y):
        self.view.start_x = start_x
        self.view.start_y = start_y
        self.view.start_slice = self.view.get_slice()

    def drag_slice(self, cur_x, cur_y):
        #moved = self.view.start_y - cur_y
        #rel = moved/10
        x1, y1, x2, y2 = self.ax.bbox.extents
        height = y2 - y1
        rel = (self.view.start_y - cur_y)/height
        slice = self.view.start_slice+rel*self.view.n_slices()
        self.view.set_slice(slice)
        self.update_image()

    def release_slice(self):
        self.view.start_x, self.view.start_y = 0,0
        self.view.start_slice = 0

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


class View(object):

    def __init__(self,  norm, slice, b_value):
        self.norm = norm
        self.slice = slice
        self.b_value = b_value

        self.start_x, self.start_y = 0,0
        self.start_slice = 0

    def n_slices(self):
        return self.smax+1

    def set_slice(self, num):
        self.slice = min(max(num, self.smin), self.smax)

    def get_slice(self):
        return self.slice

    def change_projection(self,norm_i):
        self.norm = norm_i
        self.smax = self.shape[self.norm]-1
        self.set_slice(10)

    def toggle_projection(self):
        self.change_projection((self.norm+1)%3)

    def get_axes_labels(self):
        return (MINOR_AXES[self.norm][1], MINOR_AXES[self.norm][0])

    def get_axes_aspect(self):
        x_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][1]]
        y_mm_dim = RL_DIM[MINOR_AXES_IND[self.norm][0]]
        return (y_mm_dim/x_mm_dim)

    def read_source_properties(self,source):
        if source != None:
            self.shape = source.get_shape()
            self.smin, self.smax = 0, self.shape[self.norm]-1
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
        return self.image[x]

#TODO: This nasty shit should be cleaned up once it is proof of concept
def transition(Winst, action_axis, from_template, to_template):
    transition_data = transition_data = numpy.copy(TEMPLATES[to_template])
    old_sources = numpy.copy(Winst.sources)
    view = Winst.get_view(action_axis)
    if from_template == to_template:
        pass
    elif from_template == 'NONE' and to_template == 'PROJECTION':
        pass
    elif (from_template == 'FULLSCREEN' or from_template == 'SLICES') and to_template == 'PROJECTION':
        #TODO: add the crosshair type knowledge here
        pass
    elif (from_template == 'PROJECTION' or from_template == 'SLICES') and to_template == 'FULLSCREEN':
        transition_data = numpy.copy(TEMPLATES[to_template])
        transition_data[0,0,T.ACTIVE] = 1
        transition_data[0,0,T.SOURCE] = Winst.view_to_source_ind(view)
        transition_data[0,0,T.NORM] = view.norm
        transition_data[0,0,T.SLICE] = view.slice
    elif from_template == 'SLICE' and to_template == 'FULLSCREEN':
        pass
    elif (from_template == 'FULLSCREEN' or from_template == 'PROJECTION') and to_template == 'SLICES':
        #TODO more precise maths
        n = view.n_slices()
        max_slices = 20
        jump = numpy.ceil(n/max_slices).astype(int)
        iter = max_slices-(max_slices%jump)
        gs = numpy.ceil(numpy.sqrt(iter)).astype(int)
        transition_data = numpy.zeros((gs,gs,T.N), dtype=int)
        for i in range(iter):
            x, y = i/gs, i%gs
            if i < n:
                transition_data[x,y] = [1,Winst.view_to_source_ind(view),view.norm,i*jump]
            else:
                transition_data[x,y] = [0]*T.N
    elif to_template in ('COMPARE_PROJECTION', 'COMPARE_FULLSCREEN'):
        hack = to_template[8:]
        transition_data = numpy.copy(TEMPLATES[hack])
        source_added = numpy.copy(transition_data)
        x,y,v = transition_data.shape
        print transition_data.shape
        source_added[:,:,T.SOURCE] = numpy.ones((x,y))
        transition_data = numpy.vstack((transition_data,source_added))
        #old_sources = numpy.append(old_sources, None)
    elif from_template in ('COMPARE_PROJECTION', 'COMPARE_FULLSCREEN'):
        source_ind =  Winst.view_to_source_ind(view)
        print TEMPLATES[from_template]
        transition_data = numpy.copy(TEMPLATES[to_template])
        x,y,v = transition_data.shape
        transition_data[:,:,T.SOURCE] = numpy.outer([source_ind]*x,[1]*y)
        print transition_data
        other_ind = (source_ind+1)%2
        old_sources[other_ind] = None
    else:
        print "Transition from ",from_template," to ", to_template, " not defined."
        raise RuntimeError
    print transition_data, old_sources
    return transition_data, old_sources
