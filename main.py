#
#    SuperKluge 1st prototype
#

import Globals
import os.path
import Tkinter as Tk
from Widgets import PlotViewer, SpacesViewer
from Data import Spaces
from Plot import FigureAdapter
from XML import load_xml, save_xml


# Root window
class GUI(Tk.Tk):
    def __init__(self):
        Tk.Tk.__init__(self)

        self.wm_title("SuperKluge")
        self.protocol("WM_DELETE_WINDOW", self.save)

        # Data model with some random data added
        if os.path.isfile('load.xml'):
            self.spaces, self.figure_adapter = load_xml('load.xml')
        else:
            self.spaces = Spaces()
            self.figure_adapter = FigureAdapter('1x1', self.spaces)

        # Data model viewer: a tree widget on the right side
        viewer = SpacesViewer(self, self.spaces)
        viewer.pack(side=Tk.RIGHT, fill=Tk.Y, expand=Tk.NO)
        # Plot viewer: Matplotlib 2D projections viewer into the data
        viewer = PlotViewer(self, self.figure_adapter)
        viewer.pack(side=Tk.RIGHT, fill=Tk.BOTH, expand=Tk.YES)

    # TODO: add a dialog box for saving, importing should be possible when running
    def save(self):
        save_xml('save.xml', self.spaces, self.figure_adapter)
        self.destroy()


if __name__ =='__main__':
    app = GUI()
    app.mainloop()