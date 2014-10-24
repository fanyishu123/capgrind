#!/usr/bin/env python

# CapGrind 3rd proto

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from Tkinter import *
import tkMessageBox, tkFileDialog
import WM
from WM import WM_instance, View, Image_source, UndefinedException
from custom_toolbar import NavigationToolbar2TkAgg
from widgets import ImageContextMenu, ImageList, Viewer, WM_Menu, TemplateMenu
import os

class GUI():

    def __init__(self):
        self.root = None
        self.menubar = None

        #Widgets
        self.viewer = None
        self.im_list = None
        self.wm_menu = None
        self.template_menu = None

        self.wm = None

        self.source_names = None
        self.all_sources = None

    def app(self):
        self.load_sources()

        # Root
        print "\nCreating GUI..."
        self.root = Tk()
        self.root.wm_title("CapGrind 3rd proto")

        # Menubar
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)

        # WM
        self.wm = WM_instance(self, 'FULLSCREEN', WM.TEMPLATES['FULLSCREEN'],
                              [self.all_sources[0]], self.all_sources)

        self.viewer = Viewer(self,self.wm)
        self.viewer.pack(side=RIGHT, fill=BOTH, expand=YES)

        self.im_list = ImageList(self,self.wm, self.viewer)
        self.im_list.pack(side=LEFT, fill=Y, expand=NO)

        self.wm_menu = WM_Menu(self,self.wm,self.viewer)
        self.menubar.add_cascade(label="WM", menu=self.wm_menu)
        self.template_menu = TemplateMenu(self)
        self.menubar.add_cascade(label="Templates", menu=self.template_menu)

        self.root.mainloop()

    def update_WM_menu(self):
        self.wm_menu.refresh()

    def try_change(self, template_name, n, sources = None):
        try:
            self.wm.change_template_multiple(template_name,n, use_sources=sources)
            self.viewer.redraw()
        except UndefinedException:
            tkMessageBox.showerror("Transition undefined", "Transition to "+template_name+\
                                   " is undefined from this template.")

    def load_sources(self):
        print "Loading sources..."
        # Filenames
        image_fns = ['dicomfile'+str(i+1)+'.npy' for i in range(4)]
        print "Files:", image_fns
        # Image sources
        self.all_sources = [Image_source(s) for s in image_fns]
        print "Sources:", self.all_sources
        # Image source names that happen to align with filenames above
        self.source_names = [str(s) for s in self.all_sources]



if __name__ == '__main__':

    app = GUI()
    app.app()
