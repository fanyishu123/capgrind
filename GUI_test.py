# Capgrind 4th proto

import matplotlib
matplotlib.use('TkAgg')

from Tkinter import *
import tkMessageBox, tkFileDialog

from DB import Image_source, ImageDB
from widgets import ImageList, Viewer, WM_Menu, TemplateMenu, WM_Tree
from event_handler import EventHandler

class GUI():

    def __init__(self):
        """ For documentation purposes """

        # Root widgets
        self.root = None
        self.menubar = None

        # Necessary widgets
        self.viewer = None
        self.im_list = None
        self.wm_tree = None
        self.wm_menu = None
        self.template_menu = None

        # Other objects
        self.event_handler = None
        self.image_db = None

    def app(self):
        self.event_handler = EventHandler()
        self.load_sources()

        # Root
        print "\nCreating GUI..."
        self.root = Tk()
        self.root.wm_title("CapGrind 4th proto")

        # Menubar
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)
        # Viewer and WM
        self.viewer = Viewer(self, 'FULLSCREEN', old_slots=[self.image_db.get_image('dicomfile1.npy')], n_to=1)
        # Image list widget
        self.im_list = ImageList(self)
        # Tree view widget for WM
        self.wm_tree = WM_Tree(self)
        # Menus
        self.wm_menu = WM_Menu(self)
        self.menubar.add_cascade(label="WM", menu=self.wm_menu)
        self.template_menu = TemplateMenu(self)
        self.menubar.add_cascade(label="Templates", menu=self.template_menu)

        # Image list event binding
        self.event_handler.register_view(self.image_db, 'modified', self.im_list.modified)
        self.event_handler.register_view(self.image_db, 'modified', self.wm_menu.modified)

        self.repack()
        self.root.mainloop()

    def try_transition(self, to_template, old_slots=None, action_adapter=None, n_to=None):
        self.viewer.reload(to_template, old_slots=old_slots, action_adapter=action_adapter, n_to=n_to)

    def repack(self):
        self.im_list.pack_forget()
        self.viewer.pack_forget()
        self.wm_tree.pack_forget()
        self.im_list.pack(side=LEFT, fill=Y, expand=NO)
        self.viewer.pack(side=LEFT, fill=BOTH, expand=YES)
        self.wm_tree.pack(side=LEFT, fill=Y, expand=NO)

    def update_wm_tree(self):
        self.wm_tree.refresh()

    def load_sources(self):
        print "Loading sources..."
        # Filenames
        image_fns = ['dicomfile'+str(i+1)+'.npy' for i in range(4)]
        print "Files:", image_fns
        # Image sources
        images = [Image_source(fn, self) for fn in image_fns]
        image_indentifiers = [str(im) for im in images]
        self.image_db = ImageDB(self,zip(image_indentifiers,images))


if __name__ == '__main__':
    app = GUI()
    app.app()
