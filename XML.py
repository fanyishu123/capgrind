import Data
from Plot import FigureAdapter, AxesAdapter

# TODO: This could be a lot more generic and beautiful, needs schema support as well...
# There are some subtle yet annoying issues with writing a fully generic python object <-> XML node conversion
# It is straigthforward to write a recursive function, based solely on attribute names, values, number children etc.
# but even then we need to make some assumptions about the data model because dealing with a fully generic tree model
# is very annoying and uninformative in code level. I have an lxml.objectify version that needs porting...

import xml.etree.ElementTree as ET
import xml.dom.minidom

def load_xml(fn):

    tree = ET.parse(fn)
    model = tree.getroot()
    spaces_node = model.find('Spaces')
    figure_adapter_node = model.find('FigureAdapter')

    spaces =\
    getattr(Data, spaces_node.tag)(
        [getattr(Data, space.tag)(
            [getattr(Data, child.tag)(**{key: eval(value) for key, value in child.attrib.items()}) for child in space]
        ) for space in spaces_node]
    )

    template_name = eval(figure_adapter_node.get('template_name'))
    figure_adapter = FigureAdapter(template_name, spaces)

    space_inds = eval(figure_adapter_node.get('space_inds'))
    for space_ind, adapter, adapter_node in zip(space_inds, figure_adapter.adapters,
                                                figure_adapter_node.iter('AxesAdapter')):
        [setattr(adapter, key, eval(value)) for key, value in adapter_node.attrib.items()]
        adapter.space = figure_adapter.spaces.spaces[space_ind] if space_ind is not None else None
        if space_ind is not None: adapter.reset_limits()
        adapter.updated()

    return spaces, figure_adapter

def save_xml(fn, spaces, figure_adapter):
    extract = {Data.Image: ('fn', 'cmap', 'vmin', 'vmax'),
               Data.DataOverlay: ('fn',),
               Data.DataROI: ('fn',),
               Data.HyperRectangleROI: ('c', 'r',),
               Data.HyperEllipseROI: ('c', 'r',),
               AxesAdapter: ('proj', 'a1', 'a2', 'xmin', 'xmax', 'ymin', 'ymax',)
    }

    model_node = ET.Element('Model')
    spaces_node = ET.SubElement(model_node, 'Spaces')
    for space in spaces.spaces:
        space_node = ET.SubElement(spaces_node, 'Space')
        for array in space.arrays:
            values = {key: repr(getattr(array, key)) for key in extract[type(array)]}
            if issubclass(type(array), Data.DataArray): values['origin'] = repr(array.origin())
            ET.SubElement(space_node, array.__class__.__name__, values)

    space_inds = [figure_adapter.spaces.spaces.index(adapter.space) if adapter.space else None
                  for adapter in figure_adapter.adapters]
    figure_adapter_node = ET.SubElement(model_node, 'FigureAdapter', {'template_name': repr(figure_adapter.template_name),
                                                                      'space_inds': repr(space_inds)})
    for adapter in figure_adapter.adapters:
        ET.SubElement(figure_adapter_node, 'AxesAdapter', {key: repr(getattr(adapter, key)) for key in
                                                           extract[AxesAdapter]})

    with open(fn, "w") as file:
        file.write(xml.dom.minidom.parseString(ET.tostring(model_node)).toprettyxml())
