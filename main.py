#!/usr/bin/env python

# CapGrind 2nd proto

import matplotlib
import numpy as np
from Tkinter import *
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import WM
from custom_toolbar import NavigationToolbar2TkAgg
from WM import WM_instance, View, Image_source

# implement the default mpl key bindings
#from matplotlib.backend_bases import key_press_handler

def on_key_event(event):
    print('you pressed %s'%event.key)
    #key_press_handler(event, canvas, toolbar)

def _quit():
    root.quit()     # stops mainloop
    root.destroy()  # this is necessary on Windows to prevent
                    # Fatal Python Error: PyEval_RestoreThread: NULL tstate


print "Starting..."

total_sources = 4
image_fns = ['dicomfile'+str(i+1)+'.npy' for i in range(total_sources)]
print "Files:", image_fns

# Image sources
all_sources = [Image_source(image_fns[i]) for i in range(total_sources)]
sources = [all_sources[1], None]
#print "image source 1", "("+str(sources[0])+")", "matches 1:", "("+str(sources[0])+")", np.array_equal(sources[0].image,sources[0].image)
#print "image source 1", "("+str(sources[0])+")", "matches 2:", "("+str(sources[1])+")", np.array_equal(sources[0].image,sources[1].image)
print "Sources:", sources

print "\nCreating GUI..."

# Root
root = Tk()
root.wm_title("CapGrind 2nd proto")

# Viewer frame
fr = Frame(root)
fr.pack(fill=BOTH,expand=YES)


# WM
wm = WM_instance('PROJECTION', WM.TEMPLATES['PROJECTION'], sources, all_sources)
fig = wm.get_figure()

# Image (tk.DrawingArea)
canvas = FigureCanvasTkAgg(fig, master=fr)
canvas.get_tk_widget().grid(row=1, column=1,sticky=N+E+S+W)
canvas.mpl_connect('key_press_event', on_key_event)
canvas.show()
canvas.draw()

# Menubar
menubar = Menu(root)
root.config(menu=menubar)

# Select sources
select_sources_menu = Menu(menubar, tearoff=0)
source_menu = []
source_selection = []
for i in range(len(sources)):
    source_menu.append(Menu(menubar, tearoff=0))
    select_sources_menu.add_cascade(label=str(i), menu=source_menu[-1])
    source_selection.append(IntVar())
    for j in range(total_sources):
        def f (i=i,j=j):
            wm.change_source(i,j)
            canvas.draw_idle()
        source_menu[-1].add_radiobutton(label=str(j)+" ("+str(all_sources[j])+")",
                                    variable=source_selection[-1], command=f )
menubar.add_cascade(label="Select Sources", menu=select_sources_menu)


# Button toolbar, centered below image
cfr = Frame(fr)
cfr.grid(row=2, column=1,sticky=N+E+S+W)
buttons=Frame(cfr)
buttons.pack(side=LEFT,fill=X,expand=1)

# Matplotlib toolbar
toolbar = NavigationToolbar2TkAgg(canvas, buttons, wm)
toolbar.update()

# Expand rules
Grid.rowconfigure(fr,0,weight=0)
Grid.rowconfigure(fr,1,weight=1)
Grid.rowconfigure(fr,2,weight=0)
Grid.columnconfigure(fr,0,weight=0)
Grid.columnconfigure(fr,1,weight=1)


mainloop()
