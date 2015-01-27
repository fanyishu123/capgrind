"""
.. module:: Model
   :synopsis: Contains the program state as an object and tools to import / export it as XML.
.. moduleauthor:: Markus Viljanen <majuvi@utu.fi>

.. note:: This could be a lot more generic and beautiful, needs schema support as well...

There are some subtle yet annoying issues with writing a fully generic python object <-> XML node conversion
It is straigthforward to write a recursive function, based solely on attribute names, values, number children etc.
but even then we need to make some assumptions about the data model because dealing with a fully generic tree model
is very annoying and uninformative in code level. I have an lxml.objectify version that needs porting...

The best idea seems to be to write an interface that all xml loadable / dumbable objects support (ala pickle)...

"""



import Data
from Plot import FigureAdapter, AxesAdapter
import xml.etree.ElementTree as ET
import xml.dom.minidom

class Model(object):
    """ This object holds the entire program state as an object hierarchy.
    """

    def __init__(self, gui):
        self.gui = gui

    def load(self, fn=None):
        """Load the state from a given file, or generate an empty state if none is provided.

        :param fn: Filename to load from
        :type fn: str.
        """
        self._initializing = True
        if fn:
            self.load_xml(fn)
        else:
            self.spaces = Data.Spaces(self)
            self.figure_adapter = FigureAdapter(self.gui, '1x1')
        self._initializing = False

    def save(self, fn):
        """Save the state to a given file.

        :param fn: Filename to load from
        :type fn: str.
        """
        self.save_xml(fn)

    def load_xml(self, fn):
        """Load the state from a given XML file.

        :param fn: Filename to load from
        :type fn: str.
        """
        tree = ET.parse(fn)
        model_node = tree.getroot()
        spaces_node = model_node.find('Spaces')
        figure_adapter_node = model_node.find('FigureAdapter')

        self.spaces =\
        getattr(Data, spaces_node.tag)(self,
            [getattr(Data, space.tag)(eval(space.get('key')),
                [getattr(Data, child.tag)(**{key: eval(value) for key, value in child.attrib.items()}) for child in space]
            ) for space in spaces_node]
        )

        template_name = eval(figure_adapter_node.get('template_name'))
        self.figure_adapter = FigureAdapter(self.gui, template_name)

        for adapter, adapter_node in zip(self.figure_adapter.adapters, figure_adapter_node.iter('AxesAdapter')):
            [setattr(adapter, key, eval(value)) for key, value in adapter_node.attrib.items()]
            if adapter.space_key: adapter.reset_limits()
            adapter.updated()

    def save_xml(self, fn):
        """Save the state to a given XML file.

        :param fn: Filename to save to
        :type fn: str.
        """
        extract = {Data.Image: ('fn', 'cmap', 'vmin', 'vmax'),
                   Data.DataOverlay: ('fn',),
                   Data.DataROI: ('fn',),
                   Data.HyperRectangleROI: ('c', 'r',),
                   Data.HyperEllipseROI: ('c', 'r',),
                   AxesAdapter: ('proj', 'a1', 'a2', 'xmin', 'xmax', 'ymin', 'ymax',)
        }

        model_node = ET.Element('Model')
        spaces_node = ET.SubElement(model_node, 'Spaces')
        for space in self.spaces.spaces:
            space_node = ET.SubElement(spaces_node, 'Space', {'key': repr(space.key)})
            for array in space.arrays:
                values = {key: repr(getattr(array, key)) for key in extract[type(array)]}
                if issubclass(type(array), Data.DataArray): values['origin'] = repr(array.origin())
                ET.SubElement(space_node, array.__class__.__name__, values)

        figure_adapter_node = ET.SubElement(model_node, 'FigureAdapter',
                                            {'template_name': repr(self.figure_adapter.template_name)})
        for adapter in self.figure_adapter.adapters:
            ET.SubElement(figure_adapter_node, 'AxesAdapter', {key: repr(getattr(adapter, key)) for key in
                                                               extract[AxesAdapter]})

        with open(fn, "w") as file:
            file.write(xml.dom.minidom.parseString(ET.tostring(model_node)).toprettyxml())

    def spaces_updated(self, space, spaces_container=False):
        if not self._initializing:
            self.figure_adapter.spaces_updated(space, spaces_container)
            self.gui.tree.spaces_updated(space, spaces_container)
