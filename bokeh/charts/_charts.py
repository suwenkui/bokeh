"""This is the Bokeh charts interface. It gives you a high level API to build
complex plot is a simple way.

This is the main Chart class which is able to build several plots using the low
level Bokeh API. It setups all the plot characteristics and lets you plot
different chart types, taking OrderedDict as the main input. It also supports
the generation of several outputs (file, server, notebook).
"""
#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2014, Continuum Analytics, Inc. All rights reserved.
#
# Powered by the Bokeh Development Team.
#
# The full license is in the file LICENCE.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import numpy as np

from ..models import (
    CategoricalAxis, DatetimeAxis, Grid, Legend, LinearAxis, Plot)

from ..document import Document
from ..session import Session
from ..embed import file_html
from ..resources import INLINE
from ..browserlib import view
from ..utils import publish_display_data
from ..plotting_helpers import _process_tools_arg
from ..plotting import DEFAULT_TOOLS

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------


class Chart(Plot):
    """This is the main Chart class, the core of the ``Bokeh.charts`` interface.

    This class essentially set up a "universal" Plot object containing all the
    needed attributes and methods to draw any of the Charts that you can build
    subclassing the ChartObject class.
    """
    __view_model__ = "Plot"
    __subtype__ = "Chart"
    def __init__(self, title=None, xlabel=None, ylabel=None, legend=False,
                 xscale="linear", yscale="linear", width=800, height=600,
                 tools=True, filename=False, server=False, notebook=False,
                 xgrid=True, ygrid=True, _doc=None, _session=None, **kws):
        """Common arguments to be used by all the inherited classes.

        Args:
            title (str): the title of your plot.
            xlabel (str): the x-axis label of your plot.
            ylabel (str): the y-axis label of your plot.
            legend (str): the legend of your plot. The legend content is
                inferred from incoming input.It can be ``top_left``,
                ``top_right``, ``bottom_left``, ``bottom_right``.
                It is ``top_right`` is you set it as True.
            xscale (str): the x-axis type scale of your plot. It can be
                ``linear``, ``datetime`` or ``categorical``.
            yscale (str): the y-axis type scale of your plot. It can be
                ``linear``, ``datetime`` or ``categorical``.
            width (int): the width of your plot in pixels.
            height (int): the height of you plot in pixels.
            tools (bool): to enable or disable the tools in your plot.
            filename (str or bool): the name of the file where your plot.
                will be written. If you pass True to this argument, it will use
                ``untitled`` as a filename.
            server (str or bool): the name of your plot in the server.
                If you pass True to this argument, it will use ``untitled``
                as the name in the server.
            notebook (bool): if you want to output (or not) your plot into the
                IPython notebook.
                lt: False)
            xgrid (bool, optional): whether to display x grid lines
                (default: True)
            ygrid (bool, optional): whether to display x grid lines
                (default: True)

        Attributes:
            plot (obj): main Plot object.
            categorical (bool): tag to prevent adding a wheelzoom to a
                categorical plot.
            glyphs (list): to keep track of the glyphs added to the plot.
        """
        kw = dict(title=title, plot_width=width, plot_height=height)

        self._source = None
        # list to save all the groups available in the incomming input
        self._groups = []
        self._data = dict()
        self._attr = []

        super(Chart, self).__init__(**kw)

        self.__title = title
        self.__xlabel = xlabel
        self.__ylabel = ylabel
        self.__legend = legend
        self.__xscale = xscale
        self.__yscale = yscale
        self.__width = width
        self.__height = height
        self.__enabled_tools = tools
        self.__filename = filename
        self.__server = server
        self.__notebook = notebook
        self.__xgrid = xgrid
        self.__ygrid = ygrid

        self._glyphs = []
        self._built = False

        self._builders = []
        self._renderer_map = []

        # Add to document and session if server output is asked
        if _doc:
            self._doc = _doc
        else:
            self._doc = Document()

        if self.__server:
            if _session:
                self._session = _session
            else:
                self._session = Session()

        self.check_attr()
        # create chart axis, grids and tools
        self.start_plot()

    def add_renderers(self, builder, renderers):
        self.renderers += renderers
        self._renderer_map.extend({ r._id : builder for r in renderers })

    def add_builder(self, builder):
        self._builders.append(builder)
        builder.create(self)

        # Add tools if supposed to
        if self._enabled_tools:
            # reset tools so a categorical builder can add only the
            # supported tools
            self.tools = []
            self.create_tools(self._enabled_tools)

    def create_axes(self):
        # Add axis
        self._xaxis = self.make_axis("below", self.__xscale, self.__xlabel)
        self._yaxis = self.make_axis("left", self.__yscale, self.__ylabel)

    def create_grids(self, xgrid=True, ygrid=True):
        # Add grids
        if xgrid:
            self.make_grid(0, self._xaxis.ticker)
        if ygrid:
            self.make_grid(1, self._yaxis.ticker)

    def create_tools(self, tools):
        # if no tools customization let's create the default tools
        if isinstance(tools, bool) and tools:
            tools = DEFAULT_TOOLS
        elif isinstance(tools, bool):
            # in case tools == False just exit
            return

        tool_objs = _process_tools_arg(self, tools)
        self.add_tools(*tool_objs)

    def start_plot(self):
        """Add the axis, grids and tools
        """
        self.create_axes()
        self.create_grids(self._xgrid, self._ygrid)

        # Add tools if supposed to
        if self._enabled_tools:
            self.create_tools(self._enabled_tools)

    def add_legend(self, orientation, legends):
        """Add the legend to your plot, and the plot to a new Document.

        It also add the Document to a new Session in the case of server output.

        Args:
            orientation(str): position of the legend on the chart.
            legends(List(Tuple(String, List(GlyphRenderer)): A list of
                tuples that maps text labels to the legend to corresponding
                renderers that should draw sample representations for those
                labels.
        """
        legend = Legend(orientation=orientation, legends=legends)
        self.add_layout(legend)

    def make_axis(self, location, scale, label):
        """Create linear, date or categorical axis depending on the location,
        scale and with the proper labels.

        Args:
            location(str): the space localization of the axis. It can be
                ``left``, ``right``, ``above`` or ``below``.
            scale (str): the scale on the axis. It can be ``linear``, ``datetime``
                or ``categorical``.
            label (str): the label on the axis.

        Return:
            axis: Axis instance
        """

        if scale == "linear":
            axis = LinearAxis(axis_label=label)
        elif scale == "datetime":
            axis = DatetimeAxis(axis_label=label)
        elif scale == "categorical":
            axis = CategoricalAxis(
                major_label_orientation=np.pi / 4, axis_label=label
            )

        self.add_layout(axis, location)
        return axis

    def make_grid(self, dimension, ticker):
        """Create the grid just passing the axis and dimension.

        Args:
            dimension(int): the dimension of the axis, ie. xaxis=0, yaxis=1.
            ticker (obj): the axis.ticker object

        Return:
            grid: Grid instance
        """

        grid = Grid(dimension=dimension, ticker=ticker)
        self.add_layout(grid)

        return grid

    def show(self):
        """Main show function.

        It shows the plot in file, server and notebook outputs.
        """
        # Add to document and session
        if self._server:
            if self._server is True:
                self._servername = "untitled_chart"
            else:
                self._servername = self.__server

            self._session.use_doc(self._servername)
            self._session.load_document(self._doc)

        if not self._doc._current_plot == self:
            self._doc._current_plot = self
            self._doc.add(self)

        if self._filename:
            if self._filename is True:
                filename = "untitled"
            else:
                filename = self._filename
            with open(filename, "w") as f:
                f.write(file_html(self._doc, INLINE, self.title))
            print("Wrote %s" % filename)
            view(filename)
        elif self.__filename is False and \
                        self.__server is False and \
                        self.__notebook is False:
            print("You have a provide a filename (filename='foo.html' or"
                  " .filename('foo.html')) to save your plot.")

        if self.__server:
            self.session.store_document(self._doc)
            link = self._session.object_link(self._doc.context)
            view(link)

        if self.__notebook:
            from bokeh.embed import notebook_div
            # for plot in self._plots:
            publish_display_data({'text/html': notebook_div(self)})

    ##################################################
    # Methods related to method chaining
    ##################################################
    def xlabel(self, xlabel):
        """Set the xlabel of your chart.

        Args:
            xlabel (str): the x-axis label of your plot.

        Returns:
            self: the chart object being configured.
        """
        self._xlabel = xlabel
        return self

    def ylabel(self, ylabel):
        """Set the ylabel of your chart.

        Args:
            ylabel (str): the y-axis label of your plot.

        Returns:
            self: the chart object being configured.
        """
        self._ylabel = ylabel
        return self

    def xgrid(self, xgrid):
        """Set the xgrid of your chart.

        Args:
            xgrid (bool): defines if x-grid of your plot is visible or not

        Returns:
            self: the chart object being configured.
        """
        self._xgrid = xgrid
        return self

    def ygrid(self, ygrid):
        """Set the ygrid of your chart.

        Args:
            ygrid (bool): defines if y-grid of your plot is visible or not

        Returns:
            self: the chart object being configured.
        """
        self._ygrid = ygrid
        return self

    def legend(self, legend):
        """Set the legend of your chart.

        The legend content is inferred from incoming input.
        It can be ``top_left``, ``top_right``, ``bottom_left``, ``bottom_right``.
        It is ``top_right`` is you set it as True.

        Args:
            legend (str or bool): the legend of your plot.

        Returns:
            self: the chart object being configured.
        """
        self._legend = legend
        return self

    def xscale(self, xscale):
        """Set the xscale of your chart.

        It can be ``linear``, ``datetime`` or ``categorical``.

        Args:
            xscale (str): the x-axis scale of your plot.

        Returns:
            self: the chart object being configured.
        """
        self._xscale = xscale
        return self

    def yscale(self, yscale):
        """Set the yscale of your chart.

        It can be ``linear``, ``datetime`` or ``categorical``.

        Args:
            yscale (str): the y-axis scale of your plot.

        Returns:
            self: the chart object being configured.
        """
        self._yscale = yscale
        return self

    def width(self, width):
        """Set the width of your chart.

        Args:
            width (int): the width of your plot in pixels.

        Returns:
            self: the chart object being configured.
        """
        self._width = width
        return self

    def height(self, height):
        """Set the height of your chart.

        Args:
            height (int): the height of you plot in pixels.

        Returns:
            self: the chart object being configured.
        """
        self._height = height
        return self


    def filename(self, filename):
        """Set the file name of your chart.

        If you pass True to this argument, it will use ``untitled`` as a filename.

        Args:
            filename (str or bool): the file name where your plot will be written.

        Returns:
            self: the chart object being configured.
        """
        self._filename = filename
        return self

    def server(self, server):
        """Set the server name of your chart.

        If you pass True to this argument, it will use ``untitled``
        as the name in the server.

        Args:
            server (str or bool): the name of your plot in the server

        Returns:
            self: the chart object being configured.
        """
        self._server = server
        return self

    def notebook(self, notebook=True):
        """Show your chart inside the IPython notebook.

        Args:
            notebook (bool, optional) : whether to output to the
                IPython notebook (default: True).

        Returns:
            self: the chart object being configured.
        """
        self._notebook = notebook
        return self

    def enabled_tools(self, tools=True):
        """Set your chart tools.

        Args:
            tools (bool, optional) : whether to output to the
                IPython notebook (default: True).

        Returns:
            self: the chart object being configured.
        """
        self._enabled_tools = tools
        return self

    def check_attr(self):
        """Check if any of the underscored attributes exists.

        It checks if any of the chained method were used. If they were
        not used, it assigns the parameters content by default.
        """
        if not hasattr(self, '_title'):
            self._title = self.__title
        if not hasattr(self, '_xlabel'):
            self._xlabel = self.__xlabel
        if not hasattr(self, '_ylabel'):
            self._ylabel = self.__ylabel
        if not hasattr(self, '_legend'):
            self._legend = self.__legend
        if not hasattr(self, '_xscale'):
            self._xscale = self.__xscale
        if not hasattr(self, '_yscale'):
            self._yscale = self.__yscale
        if not hasattr(self, '_width'):
            self._width = self.__width
        if not hasattr(self, '_height'):
            self._height = self.__height
        if not hasattr(self, '_enabled_tools'):
            self._enabled_tools = self.__enabled_tools
        if not hasattr(self, '_filename'):
            self._filename = self.__filename
        if not hasattr(self, '_server'):
            self._server = self.__server
        if not hasattr(self, '_notebook'):
            self._notebook = self.__notebook
        if not hasattr(self, '_xgrid'):
            self._xgrid = self.__xgrid
        if not hasattr(self, '_ygrid'):
            self._ygrid = self.__ygrid
