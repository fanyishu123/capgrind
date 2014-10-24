


#!/usr/bin/env python

import matplotlib
matplotlib.use('TkAgg')

from numpy import arange, sin, pi
from custom_toolbar import FigureCanvasTkAgg, NavigationToolbar2TkAgg
# implement the default mpl key bindings
from matplotlib.backend_bases import key_press_handler
import WM
from WM import Image_source

from matplotlib.figure import Figure
import Tkinter as Tk
import tkMessageBox, tkFileDialog
import ttk
import os



class DataRange(object):

    def __init__(self, gui, wm, viewer, ims):
        self.gui = gui
        self.wm = wm
        self.viewer = viewer
        self.ims = ims
        self.fns = [str(im) for im in self.ims]

        t2 = Tk.Toplevel(self.gui.root)
        t2.title('Data Range Editor')
        t2.transient(self.gui.root)

        # Image selection combobox
        sel_fr = Tk.Frame(master=t2)
        Tk.Label(sel_fr, text="Image:").pack(side=Tk.LEFT)
        self.imagesel = ttk.Combobox(sel_fr)
        self.imagesel['values'] = self.fns
        self.imagesel.bind('<<ComboboxSelected>>', self.update)
        self.imagesel.set(self.fns[0])
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

        def close():
            t2.destroy()
        t2.protocol('WM_DELETE_WINDOW', close)

    def set_limits(self):
        try:
            vmi = float(self.lower_limit.get())
            vma = float(self.upper_limit.get())
            # Same field, format to float
            self.llim.set(vmi)
            self.ulim.set(vma)
            # Set image kwargs to match this
            if not self.all_images.get():
                im = self.source_by_name(self.imagesel.get())
                im.kwargs['vmin'] = vmi
                im.kwargs['vmax'] = vma
            else:
                for im in self.ims:
                    im.kwargs['vmin'] = vmi
                    im.kwargs['vmax'] = vma
            print "Set values:", vmi, vma
            self.update()
        except ValueError:
            print "Error converting"

    def update(self, event=None):
        print "updating..."
        im = self.source_by_name(self.imagesel.get())
        # Read defined values into user fields
        x1 = im.kwargs['vmin']
        x2 = im.kwargs['vmax']
        self.llim.set(x1)
        self.ulim.set(x2)
        # Calculated when instanciated
        self.llim_orig.set(im.vmin)
        self.ulim_orig.set(im.vmax)
        self.a.clear()
        self.a.hist(im.image.flat, bins=256, range=(x1,x2), fc='k', ec='k')
        self.a.set_xlim(x1,x2)
        self.canvas.draw()
        self.reset_ims()

    def reset(self):
        print "resetting..."
        if not self.all_images.get():
            im = self.source_by_name(self.imagesel.get())
            im.kwargs['vmin'] = im.vmin
            im.kwargs['vmax'] = im.vmax
            self.llim.set(im.vmin)
            self.ulim.set(im.vmax)
        else:
            for im in self.ims:
                im.kwargs['vmin'] = im.vmin
                im.kwargs['vmax'] = im.vmax
        self.update()

    def source_by_name(self, name):
        return self.ims[self.fns.index(name)]

    def reset_ims(self):
        for s in self.ims:
            if s in self.wm.get_sources():
                for adapter in self.wm.get_adapters(s):
                    adapter.reset()
        self.viewer.redraw()

class ImageContextMenu(Tk.Menu):

    def __init__(self, gui, wm, viewer, imlist):
        Tk.Menu.__init__(self, master=gui.root,tearoff=0)

        self.gui = gui
        self.wm = wm
        self.viewer = viewer
        self.open_sources = imlist.get_selected()

        self.add_command(label="Open", command=self.open_in_viewer)

        self.add_command(label="Data Editor", command=self.open_data_editor)
        #self.add_command(label="ROI editor", command=self.none)

        cmap_menu = Tk.Menu(self, tearoff=0)
        self.add_cascade(label="Interpolation", menu=cmap_menu)
        #TODO: this can iterate over keys in kws
        for cn,cm in WM.Image_source.kws['interpolation'].items():
            def f (cm=cm):
                self.set_kwarg('interpolation',cm)
            cmap_menu.add_command(label=cn, command=f)

        intr_menu = Tk.Menu(self, tearoff=0)
        self.add_cascade(label="Colormap", menu=intr_menu)
        for cn,cm in WM.Image_source.kws['cmap'].items():
            def f (cm=cm):
                self.set_kwarg('cmap',cm)
            intr_menu.add_command(label=cn, command=f)

    def open_in_viewer(self):
        if self.open_sources != []:
            self.gui.try_change('FULLSCREEN', len(self.open_sources), self.open_sources)

    def open_data_editor(self):
        app = DataRange(self.gui, self.wm, self.viewer, self.open_sources)

    def set_kwarg(self,cn,cm):
        for s in self.open_sources:
            s.kwargs[cn]=cm
            if s in self.wm.get_sources():
                for adapter in self.wm.get_adapters(s):
                    adapter.reset()
        self.viewer.redraw()


class ImageList(Tk.Frame):

    def __init__(self, gui, wm, viewer):
        Tk.Frame.__init__(self, master=gui.root)
        self.gui = gui
        self.wm = wm
        self.viewer = viewer
        self.create_images_list_toolbar()
        self.create_images_list()

    def create_images_list(self):
        list_frame = Tk.Frame(self)
        self.listbox = Tk.Listbox(list_frame, activestyle='none', cursor='hand2',
                               selectmode=Tk.EXTENDED, width=20, heigh=10)
        self.listbox.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=1)
        self.listbox.bind("<Button-3>", self.show_context_menu)
        scrollbar = Tk.Scrollbar(list_frame)
        scrollbar.pack(side=Tk.RIGHT, fill=Tk.BOTH)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)
        self.update_listbox()
        list_frame.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

    def create_images_list_toolbar(self):
        topframe = Tk.Frame(self)
        add_diricon = Tk.PhotoImage(file='icons/add_dir.gif')
        add_dirbtn=Tk.Button(topframe,image=add_diricon,borderwidth=0,padx=0, text='Add Dir',
                          command=self.add_dir)
        add_dirbtn.image = add_diricon
        add_dirbtn.pack(side=Tk.LEFT, fill=Tk.NONE, expand=0)
        add_fileicon = Tk.PhotoImage(file='icons/add_file.gif')
        add_filebtn=Tk.Button(topframe,image=add_fileicon,borderwidth=0,padx=0, text='Add Source',
                           command=self.add_source)
        add_filebtn.image = add_fileicon
        add_filebtn.pack(side=Tk.LEFT, fill=Tk.NONE, expand=0)
        del_selectedicon = Tk.PhotoImage(file='icons/del_selected.gif')
        del_selectedbtn=Tk.Button(topframe,image=del_selectedicon,borderwidth=0,padx=0, text='Delete',
                               command=self.del_selected)
        del_selectedbtn.image = del_selectedicon
        del_selectedbtn.pack(side=Tk.LEFT, fill=Tk.NONE, expand=0)
        topframe.pack(side=Tk.TOP, fill=Tk.X, expand=0)


    def show_context_menu(self,event):
        if self.get_selected() != []:
            ImageContextMenu(self.gui, self.wm, self.viewer, self).tk_popup(event.x_root+45,
                                                                  event.y_root+10, 0)

    def add_dir(self):
        path = tkFileDialog.askdirectory()
        if path:
            tfileList = []
            for (dirpath, dirnames, filenames) in os.walk(path):
                for tfile in filenames:
                    if tfile.endswith(".npy"):
                        tfileList.append(dirpath+"/"+tfile)
            for fn in tfileList:
                #self.listbox.insert(END, os.path.basename(fn))
                self.gui.all_sources.append(Image_source(fn))
            self.update_listbox()


    def add_source(self):
        filename = tkFileDialog.askopenfilename(filetypes=[('All supported', '.npy')])
        if filename:
            #self.listbox.insert(END, os.path.basename(filename))
            self.gui.all_sources.append(Image_source(filename))
        self.update_listbox()


    def get_selected(self):
        selected = self.listbox.curselection()
        return [self.gui.all_sources[i] for i in selected]

    def del_selected(self):
        to_delete = self.listbox.curselection()[::-1]
        for i in to_delete:
            #self.listbox.delete(i)
            del self.gui.all_sources[i]
        self.update_listbox()

    def update_listbox(self):
        self.listbox.delete(0,Tk.END)
        for source in self.gui.all_sources:
            self.listbox.insert(Tk.END, source)

class Viewer(Tk.Frame):

    def __init__(self, gui, wm):
        Tk.Frame.__init__(self, master=gui.root)
        self.wm = wm

        # Image (tk.DrawingArea)
        fig = self.wm.get_figure()
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack(side=Tk.TOP,fill=Tk.BOTH,expand=Tk.YES)
        self.canvas.show()
        self.canvas.draw()

        # Matplotlib toolbar
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self, self.wm)
        self.toolbar.update()
        #self.toolbar.config(height=10)
        #self.toolbar.pack(side=Tk.BOTTOM,fill=Tk.X,expand=Tk.NO)

    def redraw(self):
        self.canvas.draw_idle()

class WM_Menu(Tk.Menu):

    def __init__(self,gui,wm,viewer):
        Tk.Menu.__init__(self, master=gui.menubar,tearoff=0)
        self.gui = gui
        self.wm = wm
        self.viewer = viewer

        # Select sources
        self.add_source_buttons()

    def add_source_buttons(self):
        self.source_selection = []
        for i in range(len(self.wm.sources)):
            source_menu = Tk.Menu(master=self, tearoff=0)
            self.add_cascade(label="Source "+str(i), menu=source_menu)

            v = Tk.StringVar()
            self.source_selection.append(v)
            for j in range(len(self.gui.all_sources)):
                def f (i=i,j=j):
                    self.wm.change_source(i,j)
                    self.viewer.redraw()

                source_string = str(j)+" ("+str(self.gui.all_sources[j])+")"
                if self.gui.all_sources[j] == self.wm.sources[i]: v.set(source_string)
                source_menu.add_radiobutton(label=source_string, variable=v, command=f )

    def refresh(self):
        self.delete(0, 'end')
        self.add_source_buttons()

class TemplateMenu(Tk.Menu):

    def __init__(self, gui):
        Tk.Menu.__init__(self, master=gui.menubar,tearoff=0)
        self.gui = gui
        # Select template
        self.add_template_buttons()

    def add_template_buttons(self):
        self.add_command(label="Full Screen",
                         command=lambda: self.gui.try_change('FULLSCREEN',1))
        self.add_command(label="Projection",
                         command=lambda: self.gui.try_change('PROJECTION',1))
        self.add_command(label="Slices",
                         command=lambda: self.gui.try_change('SLICES',1))
        self.add_command(label="Compare Full Screen",
                         command=lambda: self.gui.try_change('FULLSCREEN',2))
        self.add_command(label="Compare Projection",
                         command=lambda: self.gui.try_change('PROJECTION',2))

