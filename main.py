#
#    SuperKluge 1st prototype
#

import Globals
import os.path
import Tkinter as Tk
from matplotlib.figure import Figure
from Widgets import PlotViewer, SpacesViewer, MasterMenu
from Model import Model

# Root window
class GUI(Tk.Tk):
    def __init__(self):
        Tk.Tk.__init__(self)

        self.wm_title("SuperKluge")

        # Plotting backend
        self.plotter = Plotter()
        # Data model: contains array data and plotting specifications
        self.model = Model(self)
        self.model.load('load.xml' if os.path.isfile('load.xml') else None)
        # Data model viewer: a tree widget on the right side
        self.tree = SpacesViewer(self)
        self.tree.pack(side=Tk.RIGHT, fill=Tk.Y, expand=Tk.NO)
        # Plotting backend viewer: Matplotlib canvas and a toolbar on the center
        self.viewer = PlotViewer(self)
        self.viewer.pack(side=Tk.RIGHT, fill=Tk.BOTH, expand=Tk.YES)
        # Menubar
        self.menubar = MasterMenu(self)

class Plotter(object):
    def __init__(self):
        self.figure = Figure(figsize=(5,4), dpi=100)


if __name__ =='__main__':
    app = GUI()
    app.mainloop()