#!/usr/bin/env python

# CapGrind 1st proto

import matplotlib
import numpy as np
from Tkinter import *
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
# implement the default mpl key bindings
#from matplotlib.backend_bases import key_press_handler

def on_key_event(event):
    print('you pressed %s'%event.key)
    #key_press_handler(event, canvas, toolbar)

def update_image(event):
    print 'updating image...'
    view = image[slice.get(),:,:,b_value.get()]
    im.set_data(view)
    canvas.draw()

def set_cm(event=None):
        val = cmchoice.get()
        cm = cms.get(val)
        im.set_cmap(cm)
        canvas.draw()


def _quit():
    root.quit()     # stops mainloop
    root.destroy()  # this is necessary on Windows to prevent
                    # Fatal Python Error: PyEval_RestoreThread: NULL tstate



root = Tk()
root.wm_title("CapGrind 1st proto")

fig = matplotlib.figure.Figure(figsize=(5,4), dpi=100)
ax = fig.add_axes([0.0,0.0,1.0,1.0])
ax.set_xticks([])
ax.set_yticks([])

# Test image
image = np.load('dicomfile.npy')
z,y,x,b = image.shape
i,j = 0,0
kwargs = dict(interpolation='nearest', vmin=image.min(), vmax=image.max())
view = image[i,:,:,j]
im = ax.imshow(view, **kwargs)

# Viewer frame
fr = Frame(root)
fr.pack(fill=BOTH,expand=YES)

# Menubar
menubar = Menu(root)
root.config(menu=menubar)

# Color schemes
cms = {
'1. Grayscale': 'gray',
'2. Jet':'jet',
'3. Blue monotone':'Blues_r'
}
cmchoice= StringVar()
cmchoice.set('2. Jet')

# View & Color scheme menu
viewmenu = Menu(menubar, tearoff=0)
themesmenu = Menu(menubar, tearoff=0)
viewmenu.add_cascade(label="Colormap", menu=themesmenu)
for k in sorted(cms):
    themesmenu.add_radiobutton(label=k, variable=cmchoice, command=set_cm)
menubar.add_cascade(label="View", menu=viewmenu)

# B-value
b_value = IntVar()
b_value.set(0)
button_b_value=Scale(fr, from_=0, to=b-1, label='B-value', variable=b_value, orient=HORIZONTAL)
button_b_value.grid(row=0, column=1,sticky=N+E+S+W)
button_b_value.config(command=update_image)

# Slice
slice = IntVar()
slice.set(0)
button_slice=Scale(fr, from_=0, to=z-1, label='Slice', variable=slice, orient=VERTICAL)
button_slice.grid(row=1, column=0,sticky=N+E+S+W)
button_slice.config(command=update_image)

# Image (tk.DrawingArea)
canvas = FigureCanvasTkAgg(fig, master=fr)
canvas.show()
canvas.get_tk_widget().grid(row=1, column=1,sticky=N+E+S+W)
canvas.mpl_connect('key_press_event', on_key_event)

# Button toolbar, centered below image
cfr = Frame(fr)
buttons=Frame(cfr)
cfr.grid(row=2, column=1)
buttons.pack(side=BOTTOM,fill=NONE,expand=NO)

# # Pseudo buttons
# icons = ['new_file' ,'open_file', 'save', 'cut', 'copy', 'paste', 'undo', 'redo','on_find', 'about']
# for i, icon in enumerate(icons):
#     tbicon = PhotoImage(file='icons/'+icon+'.gif')
#     toolbar = Button(buttons, image=tbicon)
#     toolbar.image = tbicon
#     toolbar.pack(side=LEFT,fill=NONE,expand=NO)

# Matplotlib toolbar
toolbar = NavigationToolbar2TkAgg(canvas, buttons)
toolbar.update()

# Expand rules
Grid.rowconfigure(fr,0,weight=0)
Grid.rowconfigure(fr,1,weight=1)
Grid.rowconfigure(fr,2,weight=0)
Grid.columnconfigure(fr,0,weight=0)
Grid.columnconfigure(fr,1,weight=1)


mainloop()
