#
#   GUI widgets in the program
#
from Globals import CMAPS

import Tkinter as Tk
import ttk
import tkFileDialog
import tkMessageBox
import numpy
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #, NavigationToolbar2TkAgg
from Toolbar import NavigationToolbar2TkAgg
import Data
from Templates import STATIC_TEMPLATES

# Checks if all objects in a list are instances of a given type
all_instances = lambda l, inst : min([isinstance(o, inst) for o in l])

# Contains the plotter drawing area and the toolbar
class PlotViewer(Tk.Frame):

    def __init__(self, gui):
        Tk.Frame.__init__(self, master=gui)
        self.gui = gui
        # Image (tk.DrawingArea)
        self.canvas = FigureCanvasTkAgg(gui.plotter.figure, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP,fill=Tk.BOTH,expand=Tk.YES)
        # Matplotlib toolbar
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.gui, self)
        self.toolbar.update()

# Views the data model as a tree (forest) Spaces -> Space -> DataLayer
class SpacesViewer(Tk.Frame):
    def __init__(self, gui):
        Tk.Frame.__init__(self, master=gui)
        self.gui = gui
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
        self._clipboard = []

    def _add_tree(self):
        root_id = ''
        for space in self.gui.model.spaces.spaces:
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
                lambda self=self: self.gui.model.spaces.add_space(Data.Space()))
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
        self.add_command(label="Copy", command=self.copy_selected)
        self.add_command(label="Delete", command=self.delete_selected)

    def copy_selected(self):
        self.viewer._clipboard = self.selected

    def delete_selected(self):
        for array in self.selected:
            array.space.remove_array(array)

    def cmap_selected(self, cmap):
        for array in self.selected:
            array.set_cmap(cmap)

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
        self.add_command(label="Import Image (dicom)", command=self.import_dicom)
        self.add_command(label="Import Image (npy)", command=lambda:self.import_data(Data.Image))
        self.add_command(label="Import ROI (npy)", command=lambda:self.import_data(Data.DataROI))
        self.add_command(label="Import Overlay (npy)", command=lambda:self.import_data(Data.DataOverlay))
        if self.viewer._clipboard: self.add_command(label="Paste", command=self.paste_selected)
        self.add_command(label="Delete", command=self.delete_selected)

    def import_dicom(self):
        directory = tkFileDialog.askdirectory()
        if directory:
            try:
                cache_fn = os.path.join(os.path.abspath(directory), 'cache.npy')
                if not os.path.exists(cache_fn):
                    import dwi.dwimage
                    dwimage = dwi.dwimage.load_dicom([directory])[0]
                    numpy.save(cache_fn, dwimage.image)
                self.space.add_array(Data.Image(cache_fn))
            except ImportError:
                tkMessageBox.showerror("Missing library", "library 'dwi' not available")

    def import_data(self, DataType):
        filename = tkFileDialog.askopenfilename(filetypes=[('All supported', '.npy')])
        print filename, type(filename)
        if filename: self.space.add_array(DataType(filename))

    def add_abstract(self, DataType):
        self.space.add_array(DataType())

    def paste_selected(self):
        for array in self.viewer._clipboard:
            self.space.add_array(array)

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

class MasterMenu(Tk.Menu):

    def __init__(self, gui):
        Tk.Menu.__init__(self, master=gui,tearoff=0)
        self.gui = gui
        gui.config(menu=self)
        # File menu
        self.file_menu = FileMenu(self)
        self.add_cascade(label="File", menu=self.file_menu)
        # Plotter menu
        self.template_menu = TemplateMenu(self)
        self.add_cascade(label="Templates", menu=self.template_menu)

class TemplateMenu(Tk.Menu):

    def __init__(self, menu):
        Tk.Menu.__init__(self, master=menu,tearoff=0)
        for name in STATIC_TEMPLATES.keys():
            self.add_command(label=name, compound=Tk.LEFT,
                             command=lambda name=name: menu.gui.model.figure_adapter.set_template(name))

class FileMenu(Tk.Menu):
    def __init__(self, menu):
        Tk.Menu.__init__(self, master=menu,tearoff=0)
        self.gui = menu.gui
        self.add_command(label="Open State (XML)", compound=Tk.LEFT, command=self._open)
        self.add_command(label="Save State (XML)", compound=Tk.LEFT, command=self._save)

    def _open(self):
        filename = tkFileDialog.askopenfilename(filetypes=[('All supported', '.xml')])
        if filename: self.gui.model.load_xml(filename)

    def _save(self):
        filename = tkFileDialog.asksaveasfilename(filetypes=[('All supported', '.xml')], defaultextension='.xml')
        if filename: self.gui.model.save_xml(filename)

