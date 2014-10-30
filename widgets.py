import os
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from custom_toolbar import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import Tkinter as Tk
import ttk
import tkMessageBox, tkFileDialog

import WM
from WM import UndefinedException, transition
import DB

class DataRange(object):

    def __init__(self, gui, ids):
        self.gui = gui
        self.ids = ids
        self.cur_im = None

        t2 = Tk.Toplevel(self.gui.root)
        t2.title('Data Range Editor')
        t2.transient(self.gui.root)

        # Image selection combobox
        sel_fr = Tk.Frame(master=t2)
        Tk.Label(sel_fr, text="Image:").pack(side=Tk.LEFT)
        self.imagesel = ttk.Combobox(sel_fr)
        self.imagesel['values'] = self.ids
        self.imagesel.bind('<<ComboboxSelected>>', self.changed)

        id = self.ids[0]
        im = self.get_image(id)
        self.imagesel.set(id)
        self.gui.event_handler.register_view(im, 'modified', self.update)
        self.cur_im = im

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
            self.gui.event_handler.unregister_view(self.cur_im, 'modified', self.update)
            t2.destroy()
        t2.protocol('WM_DELETE_WINDOW', close)

    def changed(self, event):
        im = self.get_image(self.imagesel.get())
        self.gui.event_handler.unregister_view(self.cur_im, 'modified', self.update)
        self.gui.event_handler.register_view(im, 'modified', self.update)
        self.cur_im = im
        self.update()

    def set_limits(self):
        try:
            vmi = float(self.lower_limit.get())
            vma = float(self.upper_limit.get())
            # Same field, format to float
            self.llim.set(vmi)
            self.ulim.set(vma)
            # Set image kwargs to match this
            if not self.all_images.get():
                im = self.get_image(self.imagesel.get())
                im.set_kwarg(vmin = vmi, vmax = vma)
            else:
                for im in self.get_images():
                    im.set_kwarg(vmin = vmi, vmax = vma)
            print "Set values:", vmi, vma
        except ValueError:
            print "Error converting"

    def update(self, event=None):
        print "updating..."
        print self.imagesel.get()
        im = self.get_image(self.imagesel.get())
        # Read defined values into user fields
        x1 = im.get_kwarg('vmin')
        x2 = im.get_kwarg('vmax')
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
        print "resetting..."
        if not self.all_images.get():
            im = self.get_image(self.imagesel.get())
            im.set_kwarg(vmin = im.vmin, vmax = im.vmax)
            self.llim.set(im.vmin)
            self.ulim.set(im.vmax)
        else:
            for im in self.get_images():
                im.set_kwarg(vmin = im.vmin, vmax = im.vmax)

    def get_image(self, id):
        return self.gui.image_db.get_image(id)

    def get_images(self):
        return [self.gui.image_db.get_image(id) for id in self.ids]


class ImageContextMenu(Tk.Menu):

    def __init__(self, gui, selected_ids):
        Tk.Menu.__init__(self, master=gui.root,tearoff=0)

        self.gui = gui
        self.selected_ids = selected_ids
        self.selected_ims = [self.gui.image_db.get_image(i) for i in selected_ids]

        self.add_command(label="Open", command=self.open_in_viewer)

        self.add_command(label="Data Editor", command=self.open_data_editor)
        #self.add_command(label="ROI editor", command=self.none)

        for (kwarg_key, kwarg_vals), (kwarg_key_label, kwarg_vals_label) in zip(DB.Image_source.kws,
                                                                                DB.Image_source.kwls):
            menu = Tk.Menu(self, tearoff=0)
            self.add_cascade(label=kwarg_key_label, menu=menu)
            for kwarg_val, kwarg_val_label in zip(kwarg_vals, kwarg_vals_label):
                menu.add_command(label=kwarg_val_label, command =\
                lambda kwarg_key=kwarg_key,kwarg_val=kwarg_val : self._set_options(kwarg_key,kwarg_val))

    def open_in_viewer(self):
        if self.selected_ims != []:
            self.gui.try_transition('FULLSCREEN', old_slots=self.selected_ims,
                                    n_to=len(self.selected_ims))

    def open_data_editor(self):
        app = DataRange(self.gui, self.selected_ids)

    def _set_options(self,cn,cm):
        [s.set_option(cn, cm) for s in self.selected_ims]


class ImageList(Tk.Frame):

    def __init__(self, gui):
        Tk.Frame.__init__(self, master=gui.root)
        self.gui = gui
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
        list_frame.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        self.modified()


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
            ImageContextMenu(self.gui, self.get_selected_ids()).tk_popup(event.x_root+45, event.y_root+10, 0)

    def add_dir(self):
        path = tkFileDialog.askdirectory()
        if path:
            tfileList = []
            for (dirpath, dirnames, filenames) in os.walk(path):
                for tfile in filenames:
                    if tfile.endswith(".npy"):
                        tfileList.append(dirpath+"/"+tfile)
            for fn in tfileList:
                im = DB.Image_source(fn)
                self.gui.image_db.add_image(str(im),im)
            #self.update_listbox()


    def add_source(self):
        filename = tkFileDialog.askopenfilename(filetypes=[('All supported', '.npy')])
        if filename:
            im = DB.Image_source(filename)
            self.gui.image_db.add_image(str(im),im)

    def get_selected_ids(self):
        return [self.listbox.get(i) for i in self.listbox.curselection()]

    def get_selected(self):
        return [self.gui.image_db.get_image(id) for id in self.get_selected_ids()]

    def del_selected(self):
        selected = [self.listbox.get(i) for i in self.listbox.curselection()]
        self.gui.image_db.del_images(*selected)

    def modified(self):
        self.listbox.delete(0,Tk.END)
        [self.listbox.insert(Tk.END, id) for id in self.gui.image_db.identifiers()]


class Viewer(Tk.Frame):

    #TODO: transition could be prettier
    def __init__(self, gui, to_template, old_slots=None, action_adapter=None, n_to=None):
        Tk.Frame.__init__(self, master=gui.root)
        self.gui = gui
        wm = self.transition(to_template, old_slots=old_slots, action_adapter=action_adapter, n_to=n_to)
        print "Initializing viewer with wm",wm,"..."
        print wm
        print wm.slots
        for slot in wm.slots:
            print "slot", slot, "image", slot.image
            print "\tadapters", slot.adapters, "axes", [adapter.axes for adapter in slot.adapters]
        self.wm = wm
        # Image (tk.DrawingArea)
        fig = self.wm.fig
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack(side=Tk.TOP,fill=Tk.BOTH,expand=Tk.YES)
        self.canvas.show()
        self.canvas.draw()
        # Matplotlib toolbar
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self, gui)
        self.toolbar.update()
        self.bind_viewer()

    def reload(self, to_template, old_slots=None, action_adapter=None, n_to=None):
        self.unbind_viewer()
        self.viewer = Viewer.__init__(self, self.gui, to_template, old_slots=old_slots,
                                      action_adapter=action_adapter, n_to=n_to)
        self.bind_viewer()
        self.gui.wm_menu.refresh()
        self.gui.wm_tree.refresh()
        self.gui.repack()
        self.redraw()

    def transition(self, to_template, old_slots=None, action_adapter=None, n_to=None):
        # same as dynamic kwarg: old_slots=self.viewer.wm.get_images()
        old_slots = self.wm.get_images() if not old_slots else old_slots
        try:
            return transition(self.gui, to_template, old_slots, action_adapter,n_to)
        except UndefinedException:
            tkMessageBox.showerror("Transition undefined", "Transition to " + to_template +\
                                   " is undefined from this state.")

    def bind_viewer(self):
        # WM
        def wm_modified():
            self.gui.wm_tree.refresh()
            self.gui.wm_menu.refresh()
        self.gui.event_handler.register_view(self.wm, 'modified', wm_modified)
        # Images
        for im in self.gui.image_db.get_images():
            def im_modified(im=im):
                self.wm.reset_all_adapters(im)
                self.redraw()
            self.gui.event_handler.register_view(im, 'modified', im_modified )

    def unbind_viewer(self):
        self.gui.event_handler.unregister_views(self.wm)
        [self.gui.event_handler.unregister_views(im) for im in self.gui.image_db.get_images()]

    def redraw(self):
        self.canvas.draw_idle()


class WM_Tree(Tk.Frame):

    def __init__(self, gui):
        self.gui = gui
        Tk.Frame.__init__(self, master=gui.root)
        self.tree = ttk.Treeview(self, columns=('info'))
        self.tree.column('info', width=250)
        self.tree.column('#0', width=125)

        self.id_root = self.tree.insert('','end',text='WM', values=(str(self.gui.viewer.wm),), open=True)
        self.add_nodes()

        self.tree.pack(side=Tk.RIGHT, fill=Tk.BOTH, expand=Tk.YES)

    def add_nodes(self):
        for i,slot in enumerate(self.gui.viewer.wm.slots):
            id1 = self.tree.insert(self.id_root,'end',text='Slot '+str(i), values=(str(slot),), open=True)
            self.tree.insert(id1,'end',text='Image', values=(str(slot.image),), open=True)
            point = None if not slot.point else "%.2f, %.2f, %.2f"%tuple(slot.point)
            self.tree.insert(id1,'end',text='Point', values=(point,), open=True)
            id2 = self.tree.insert(id1,'end',text='Views', open=True)
            for j,adapter in enumerate(slot.adapters):
                self.tree.insert(id2, 'end', 'view'+str(i)+str(j), text='View '+str(j),
                                       values=(str(adapter),), tags='view', open=True)
                #self.tree.insert(id3, 'end', text='Axes', values=(str(adapter.axes,)))
            self.tree.insert(id1,'end',text='ROIs', open=True)

    # TODO: this needs an intelligent update function. Instead of regenerating the tree, we need to commit
    # TODO: the corresponding changes. Figure out the best way to keep the WM tree and the id tree in sync.
    def refresh(self):
        self.tree.delete(self.id_root)
        self.id_root = self.tree.insert('','end',text='WM', values=(str(self.gui.viewer.wm),), open=True)
        self.add_nodes()


class WM_Menu(Tk.Menu):

    def __init__(self,gui):
        Tk.Menu.__init__(self, master=gui.menubar,tearoff=0)
        self.gui = gui

        # Select sources
        self.add_source_buttons()

    #TODO: This should have seperate routines for initialization and modification,
    #TODO: i.e register functions to change in each slot/adapter that reset the str() here
    def add_source_buttons(self):
        self.source_selection = []
        for i, slot in enumerate(self.gui.viewer.wm.slots):
            source_menu = Tk.Menu(master=self, tearoff=0)
            self.add_cascade(label="Slot "+str(i), menu=source_menu)

            v = Tk.StringVar()
            self.source_selection.append(v)
            for id in self.gui.image_db.identifiers():
                def f (slot=slot,id=id):
                    slot.set_image(id)
                    self.gui.viewer.redraw()
                source_string = str(id)+" ("+str(self.gui.image_db.get_image(id))+")"
                if self.gui.image_db.get_image(id) == slot.image: v.set(source_string)
                source_menu.add_radiobutton(label=source_string, variable=v, command=f )
        self.add_separator()
        self.add_command(label="Add Slot", command=self.gui.viewer.wm.add_slot)
        self.add_command(label="Remove Unused Slots", command=self.gui.viewer.wm.remove_unused_slots)

    def refresh(self):
        self.delete(0, 'end')
        self.add_source_buttons()

    def modified(self):
        self.refresh()


class TemplateMenu(Tk.Menu):

    def __init__(self, gui):
        Tk.Menu.__init__(self, master=gui.menubar,tearoff=0)
        self.gui = gui
        # Select template
        self.add_template_buttons()

    def add_template_buttons(self):
        for template_name in WM.TEMPLATES.keys():
            self.add_command(label=template_name, command =\
                lambda template_name=template_name: self.gui.try_transition(template_name))
        self.add_command(label="Compare Full Screen",
                         command=lambda: self.gui.try_transition('FULLSCREEN',n_to=2))
        self.add_command(label="Compare Projection",
                         command=lambda: self.gui.try_transition('PROJECTION',n_to=2))
