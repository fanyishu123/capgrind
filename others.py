from matplotlib.lines import Line2D

class HUD(object):

    def __init__(self):
        self.HUD = dict(slot_index = None, crosshair = None, msg = None)
        self.create_slot_index()
        self.create_msg()
        self.create_crosshair()

    def draw_axes_labels(self):
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        x,y = self.get_axes_labels()
        self.axes.set_xlabel(x)
        self.axes.set_ylabel(y)

    def create_slot_index(self):
        self.HUD['slot_index']= self.axes.text(0.05, 0.95, "", fontsize=14, color='green', fontweight='bold',
                                               va='top', transform=self.axes.transAxes)

    def draw_slot_index(self):
        self.HUD['slot_index'].set(text=self.slot.index())

    def remove_slot_index(self):
        self.axes.texts.remove(self.HUD['slot_index'])

    def create_msg(self):
        self.HUD['msg']= self.axes.text(0.5, 0.5, "No Image", fontsize=10, color='red',style='italic',
                                               clip_box=(0.0,0.0,1.0,1.0), clip_on=True, va='center', ha='center',
                                               transform=self.axes.transAxes,visible=False)

    def draw_msg(self, visible):
        self.HUD['msg'].set(visible=visible)

    def remove_msg(self):
        self.axes.texts.remove(self.HUD['msg'])

    def create_crosshair(self):
        l1 = Line2D((0,0),(0,0),visible=False)
        l2 = Line2D((0,0),(0,0),visible=False)
        self.axes.lines.extend((l1,l2))
        self.HUD['crosshair'] = (l1,l2)

    def draw_crosshair(self):
        x1, x2 = self.axes.get_xlim()
        y1, y2 = self.axes.get_ylim()
        l1, l2 = self.HUD['crosshair']
        if self._has_point():
            x,y = self.get_point_xy()
            l1.set(xdata=[x, x], ydata=[y1, y2], transform=self.axes.transData,visible=True)
            l2.set(xdata=[x1, x2], ydata=[y, y], transform=self.axes.transData,visible=True)
        else:
            l1.set(visible=False)
            l2.set(visible=False)

    def remove_crosshair(self):
        l1, l2 = self.HUD['crosshair']
        self.axes.lines.remove(l1)
        self.axes.lines.remove(l2)
        self.HUD['crosshair'] = (None,None)

    def HUD_draw(self, msg_visible):
        self.draw_slot_index()
        self.draw_msg(msg_visible)
        self.draw_axes_labels()
        self.draw_crosshair()
