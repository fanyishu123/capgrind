#
#   GUI widgets in the program
#
from Globals import CMAPS

import Tkinter as Tk
import ttk
import tkFileDialog

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #, NavigationToolbar2TkAgg
from Toolbar import NavigationToolbar2TkAgg
import Data
import numpy

# Checks if all objects in a list are instances of a given type
all_instances = lambda l, inst : min([isinstance(o, inst) for o in l])

# Contains the plotter drawing area and the toolbar
class PlotViewer(Tk.Frame):

    def __init__(self, root, figure_adapter):
        Tk.Frame.__init__(self, master=root)
        self.figure_adapter = figure_adapter
        # Image (tk.DrawingArea)
        self.canvas = FigureCanvasTkAgg(self.figure_adapter.figure, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP,fill=Tk.BOTH,expand=Tk.YES)
        # Matplotlib toolbar
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)##Toolbar
        self.toolbar.update()

# Views the data model as a tree (forest) Spaces -> Space -> DataLayer
class SpacesViewer(Tk.Frame):
    def __init__(self, root, spaces):
        Tk.Frame.__init__(self, master=root)
        self.spaces = spaces
        spaces._callbacks.append(self.spaces_updated)
        self.tree = ttk.Treeview(self, columns=('info'))
        self.tree.column('info', width=150)
        self.tree.column('#0', width=100)

        self.scrollbar = Tk.Scrollbar(self)
        self.scrollbar.pack(side=Tk.RIGHT, fill=Tk.BOTH)
        self.tree.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)

        self.tree.pack(fill=Tk.BOTH, expand=Tk.YES)
        self.tree.bind('<Button-3>', self.show_context_menu)

        self._id_to_object = dict()
        self._add_tree()

    def _add_tree(self):
        root_id = ''
        for space in self.spaces.spaces:
            id1 = self.tree.insert(root_id, 'end',text=space.__class__.__name__, values=(str(space),), open=True)
            self._id_to_object[id1] = space
            for layer in space.arrays:
                id2 = self.tree.insert(id1, 'end',text=layer.__class__.__name__, values=(str(layer),), open=True)
                self._id_to_object[id2] = layer

    def _del_tree(self):
        [self.tree.delete(i) for i in self.tree.get_children()]

    def spaces_updated(self, space, spaces_container=False):
        self._del_tree()
        self._add_tree()

    def show_context_menu(self,event):
        selection = self.tree.selection()
        if selection:
            objects = [self._id_to_object[id] for id in selection]
            if all_instances(objects, Data.Data):
                DataArrayContextMenu(self, objects, all_images=all_instances(objects, Data.Image))\
                    .tk_popup(event.x_root, event.y_root, 0)
            elif len(objects) == 1 and all_instances(objects, Data.Space):
                SpaceContextMenu(self, objects[0]).tk_popup(event.x_root, event.y_root, 0)
        else:
            menu = Tk.Menu(self, tearoff=0)
            menu.add_command(label="Add Space", command=\
                lambda self=self: self.spaces.add_space(Data.Space()))
            menu.tk_popup(event.x_root, event.y_root, 0)

# Right click menu for a DataLayer object
class DataArrayContextMenu(Tk.Menu):

    def __init__(self, viewer, selected, all_images=False):
        Tk.Menu.__init__(self, master=viewer, tearoff=0)
        self.viewer = viewer
        self.selected = selected
        if all_images:
            menu = Tk.Menu(self, tearoff=0)
            self.add_command(label="Data Range",
                             command=lambda self=self, selected=selected: DataRangeEditor(self.viewer, selected))
            self.add_cascade(label="Colormap", menu=menu)
            for name, cmap in CMAPS.items():
                menu.add_command(label=name, command=lambda cmap=cmap: self.cmap_selected(cmap))
            self.add_command(label="Delete", command=self.delete_selected)##Fan
        else:
            self.add_command(label="Delete", command=self.delete_selected)##Fan
            if all_instances(selected,Data.HyperEllipseROI):##Fan
                self.add_command(label="Export ROI", command=self.saveEllipsemask)##Fan
            if all_instances(selected,Data.HyperRectangleROI):#Fan
                self.add_command(label="Export ROI", command=self.saveRectanglemask)##Fan
    def delete_selected(self):
        for array in self.selected:
            array.space.remove_array(array)

    def cmap_selected(self, cmap):
        for array in self.selected:
            array.set_cmap(cmap)

    def saveEllipsemask(self): ##FAN
        size=self.selected[0].space.arrays[0].image.shape
        r = self.selected[0].r
        c = self.selected[0].c
        r_string = "_r=(%d,%d,%d,%d)"%(r[0],r[1],r[2],r[3])
        c_string ="_c=(%d,%d,%d,%d)"%(c[0],c[1],c[2],c[3])
        filename = self.selected[0].space.arrays[0].fn+"_"+"Ellipse"+r_string+c_string
        mask = numpy.zeros(size);
        for x in range(size[0]):
            for y in range(size[1]):
                for z in range(size[2]):
                    m = ((x-c[0])/r[0])**2+ ((y-c[1])/r[1])**2+((z-c[2])/r[2])**2
                    if m<=1:
                        mask[x][y][z][c[3]]=1
        numpy.save(filename, mask)

    def saveRectanglemask(self): ##Fan
        size=self.selected[0].space.arrays[0].image.shape
        r = self.selected[0].r
        c = self.selected[0].c
        r_string = "_r=(%d,%d,%d,%d)"%(r[0],r[1],r[2],r[3])
        c_string ="_c=(%d,%d,%d,%d)"%(c[0],c[1],c[2],c[3])
        filename = self.selected[0].space.arrays[0].fn+"_"+"Rectangle"+r_string+c_string
        mask = numpy.zeros(size);
        for x in range(size[0]):
            for y in range(size[1]):
                for z in range(size[2]):
                    if abs(x-c[0])<=r[0] and abs(x-c[1])<=r[1] and abs(x-c[2])<=r[2] :
                        mask[x][y][z][c[3]]=1

        numpy.save(filename, mask)
# Right click menu for a Space object
class SpaceContextMenu(Tk.Menu):

    def __init__(self, viewer, space):
        Tk.Menu.__init__(self, master=viewer, tearoff=0)
        self.viewer = viewer
        self.space = space
        self.menu = Tk.Menu(self, tearoff=0)
        self.add_cascade(label="Add", menu=self.menu)
        for cls in (Data.HyperRectangleROI, Data.HyperEllipseROI):
            self.menu.add_command(label=str(cls.__name__), command=lambda cls=cls: self.add_abstract(cls))
        self.add_command(label="Import Image", command=lambda:self.import_data(Data.Image))
        self.add_command(label="Import ROI", command=lambda:self.import_data(Data.DataROI))
        self.add_command(label="Import Overlay", command=lambda:self.import_data(Data.DataOverlay))
        self.add_command(label="Delete", command=self.delete_selected)

    def import_data(self, DataType):
        filename = tkFileDialog.askopenfilename(filetypes=[('All supported', '.npy')])
        if filename: self.space.add_array(DataType(filename))

    def add_abstract(self, DataType):
        self.space.add_array(DataType())

    def delete_selected(self):
        self.space.spaces.remove_space(self.space)

#TODO: min/max sampling needs to be faster and or have some sort of 'updating...' indicator
# Data range editor given images
class DataRangeEditor(object):

    def __init__(self, viewer, selected):
        self.selected = selected
        self.ids = [str(i) + " - " + str(s) for i, s in enumerate(selected)]
        t2 = Tk.Toplevel(viewer)
        t2.title('Data Range Editor')
        t2.transient(viewer)

        # Image selection combobox
        sel_fr = Tk.Frame(master=t2)
        Tk.Label(sel_fr, text="Image:").pack(side=Tk.LEFT)
        self.imagesel = ttk.Combobox(sel_fr)
        self.imagesel['values'] = [str(s) for s in selected]
        self.imagesel.bind('<<ComboboxSelected>>', self.update)

        im = self.selected[0]
        self.imagesel.set(self.ids[0])

        self.imagesel.pack(side=Tk.LEFT)
        sel_fr.pack(side=Tk.TOP)

        # Grid showing current vmin, vmax and original vmin,vmax
        lim_fr = Tk.Frame(master=t2)
        Tk.Label(lim_fr, text="Upper limit:").grid(row=1,column=1)
        Tk.Label(lim_fr, text="Lower limit:").grid(row=2,column=1)

        self.ulim_orig, self.llim_orig = Tk.StringVar(), Tk.StringVar()
        self.ulim, self.llim = Tk.StringVar(), Tk.StringVar()

        self.upper_limit = Tk.Entry(lim_fr, textvariable=self.ulim)
        self.lower_limit = Tk.Entry(lim_fr, textvariable=self.llim)
        self.upper_limit.grid(row=1,column=2)
        self.lower_limit.grid(row=2,column=2)

        upper_limit_orig = Tk.Entry(lim_fr, textvariable=self.ulim_orig, state=Tk.DISABLED)
        lower_limit_orig = Tk.Entry(lim_fr, textvariable=self.llim_orig, state=Tk.DISABLED)
        upper_limit_orig.grid(row=1,column=3)
        lower_limit_orig.grid(row=2,column=3)

        lim_fr.pack(side=Tk.BOTTOM, fill=Tk.NONE, expand=0)

        # Button frame
        buttons = Tk.Frame(master=t2)
        self.all_images = Tk.BooleanVar()
        self.all_images.set(False)
        Tk.Checkbutton(buttons, text="Apply to all images", variable=self.all_images).pack(side=Tk.TOP)
        apply = Tk.Button(master=buttons, text='Apply', command=self.set_limits)
        apply.pack(side=Tk.RIGHT)
        reset = Tk.Button(master=buttons, text='Reset', command=self.reset)
        reset.pack(side=Tk.RIGHT)
        buttons.pack(side=Tk.BOTTOM, fill=Tk.NONE, expand=0)

        # Matplotlib figure
        f = Figure(figsize=(5,4), dpi=100)
        self.a = f.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(f, master=t2)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

        self.update()

    def set_limits(self):
        try:
            vmi = float(self.lower_limit.get())
            vma = float(self.upper_limit.get())
            if not self.all_images.get():
                im = self._selection_to_obj()
                im.set_vlims(vmi, vma)
            else:
                for im in self.selected:
                    im.set_vlims(vmi, vma)
            self.update()
        except ValueError:
            print "Error converting"

    def update(self, event=None):
        im = self._selection_to_obj()
        # Read defined values into user fields
        x1 = im.vmin
        x2 = im.vmax
        self.llim.set(x1)
        self.ulim.set(x2)
        # Calculated when instanciated
        self.llim_orig.set(im.vmin)
        self.ulim_orig.set(im.vmax)
        self.a.clear()
        self.a.hist(im.image.flat, bins=256, range=(x1,x2), fc='k', ec='k')
        self.a.set_xlim(x1,x2)
        self.canvas.draw()

    def reset(self):
        if not self.all_images.get():
            im = self._selection_to_obj()
            im.set_vlims(im.image.min().item(), im.image.max().item())
            self.llim.set(im.vmin)
            self.ulim.set(im.vmax)
        else:
            for im in self.selected:
                im.set_vlims(im.image.min().item(), im.image.max().item())

    def _selection_to_obj(self):
        return self.selected[self.ids.index(self.imagesel.get())]