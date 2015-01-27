#
#   Templates for the plot viewer
#
from Globals import NORM_3D

# Copies adapter properities from source into destination
def copy_adapter(dest, source):
    dest.space = source.get_space()
    dest.set_axes(source.a1, source.a2)
    dest.set_proj(source.proj)
    dest.set_axes_limits(((source.xmin, source.xmax), (source.ymin, source.ymax)))

# Copies clicked adapter
def FULLSCREEN(fig_adapter, adapter):
    a = fig_adapter.adapters[0]
    copy_adapter(a, adapter)

# Produces a 3D projection of a clicked point
def PROJECTION(fig_adapter, adapter):
    for t, i in NORM_3D.items():
        a = fig_adapter.adapters[i]
        a.space_key = adapter.space_key
        a.set_axes(t[0], t[1])
        a.set_proj(adapter.proj)
        a.center_to_point()
        a.set_axes_zoom(adapter.get_axes_zoom())

#TODO: would be nice to have either unbinded views or full shifted subslices instead of repeated slices on edges...
# Produces slices around a point to clicked adapter direction
def SLICES(fig_adapter, adapter):
    i = NORM_3D.keys().index((adapter.a1, adapter.a2))
    l, n = len(fig_adapter.adapters), adapter.get_axis_length(i)
    I = [min(n-1,max(0,v)) for v in range(int(adapter.proj[i]-l/2), int(adapter.proj[i]+l/2+1))]
    for j, a in zip(I, fig_adapter.adapters):
        copy_adapter(a, adapter)
        a.set_proj_axis(i, j)


# TEMPLATE:
#   ( grid size, list of (view placement on grid), list of (view space index), post processing function )

DYNAMIC_TEMPLATES = {
    'FULLSCREEN' : ((1,1), [(0,0)], [0], FULLSCREEN),
    'PROJECTION' : ((1,3), [(0,0),(0,1),(0,2)], [0,0,0], PROJECTION),
    'SLICES' : ((3,3), [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0),(2,1),(2,2)], [0,0,0,0,0,0,0,0,0], SLICES),
}

STATIC_TEMPLATES = {
    '1x1' : ((1,1), [(0,0)], [0], None),
    '1x2' : ((1,2), [(0,0),(0,1)], [0,1], None),
    '1x3' : ((1,3), [(0,0),(0,1),(0,2)], [0,0,0], None),
    '2x1' : ((2,1), [(0,0),(1,0)], [0,1], None),
    '2x2' : ((2,2), [(0,0),(0,1),(1,0),(1,1)], [0,0,1,1], None),
    '3x2' : ((3,2), [(0,0),(0,1),(1,0),(1,1),(2,0),(2,1)], [0,1,0,1,0,1], None),
    '2x3' : ((2,3), [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)], [0,0,0,1,1,1], None),
    '3x3' : ((3,3), [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0),(2,1),(2,2)], [0,0,0,1,1,1,2,2,2], None),
    '2x1s' : ((2,2), [(slice(None),0),(0,1),(1,1)], [0,0,0], None),
    '1sx2' : ((2,2), [(0,0),(1,0),(slice(None),1)], [0,0,0], None),
}
