#
#  This file is part of Bakefile (http://www.bakefile.org)
#
#  Copyright (C) 2012 Vaclav Slavik
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.
#

"""
Base classes for all Visual Studio toolsets.
"""

import uuid
import types
from xml.sax.saxutils import escape, quoteattr

import bkl.expr
from bkl.utils import OrderedDict


# Namespace constants for the GUID function
NAMESPACE_PROJECT   = uuid.UUID("{D9BD5916-F055-4D77-8C69-9448E02BF433}")
NAMESPACE_SLN_GROUP = uuid.UUID("{2D0C29E0-512F-47BE-9AC4-F4CAE74AE16E}")
NAMESPACE_INTERNAL =  uuid.UUID("{BAA4019E-6D67-4EF1-B3CB-AE6CD82E4060}")

def GUID(namespace, solution, data):
    """
    Generates GUID in given namespace, for given solution (bkl project), with
    given data (typically, target ID).
    """
    g = uuid.uuid5(namespace, '%s/%s' % (str(solution), str(data)))
    return "{%s}" % str(g).upper()


class Node(object):
    """
    Convenience representation of XML node for project file output. It provides
    two useful features:

      1. Ability to concisely specify attributes
      2. Values aren't limited to strings, they may be any Python objects
         convertible to strings. In particular, they may be
         :class:`bkl.expr.Expr` instances and they will be formatted correctly.

    Attributes are added to the node using keyword arguments to the constructor
    or using dictionary-like access:
    >>> node["Label"] = "PropertySheets"

    Child nodes are added using the :meth:`add()` method.
    """
    def __init__(self, name, text=None, **kwargs):
        """
        Creates an XML node with given element name. If provided, the text is
        used for its textual content. Any provided keyword arguments are used
        to add attributes to the node.

        Examples:

        >>> Node("ImportGroup", Label="PropertySheets", Foo="A")
            # creates <ImportGroup Label="PropertySheets" Foo="a"/>
        >>> Node("LinkIncremental", True)
            # creates <LinkIncremental>true</LinkIncremental>
        """
        self.name = name
        self.text = text
        self.attrs = OrderedDict()
        self.children = []
        self.attrs.update(kwargs)

    def __setitem__(self, key, value):
        self.attrs[key] = value

    def __getitem__(self, key):
        return self.attrs[key]

    def add(self, *args, **kwargs):
        """
        Add a child to this node. There are several ways of invoking add():

        The argument may be another node:
        >>> n.add(Node("foo"))

        Or it may be key-value pair, where the value is bkl.expr.Expr or any
        Python value convertible to string; the first argument is name of child
        element and the second one is its textual value:
        >>> n.add("ProjectGuid", "{31DC1570-67C5-40FD-9130-C5F57BAEBA88}")
        >>> n.add("LinkIncremental", target["vs-incremental-link"])

        Or it can take the same arguments that Node constructor takes; this is
        equivalent to creating a Node using the same arguments and than adding
        it using the first form of add():
        >>> n.add("ImportGroup", Label="PropertySheets")
        """
        assert len(args) > 0
        arg0 = args[0]
        if len(args) == 1:
            if isinstance(arg0, Node):
                self.children.append((arg0.name, arg0))
                return
            elif isinstance(arg0, types.StringType):
                self.children.append((arg0, Node(arg0, **kwargs)))
                return
        elif len(args) == 2:
            if isinstance(arg0, types.StringType) and len(kwargs) == 0:
                    self.children.append((arg0, args[1]))
                    return
        assert 0, "add() is confused: what are you trying to do?"

    def has_children(self):
        return len(self.children) > 0


class VSExprFormatter(bkl.expr.Formatter):
    list_sep = ";"

    def reference(self, e):
        assert False, "All references should be expanded in VS output"

    def bool_value(self, e):
        return "true" if e.value else "false"


XML_HEADER = """\
<?xml version="1.0" encoding="utf-8"?>
<!-- This file was generated by Bakefile (http://bakefile.org). Do not modify, all changes will be overwritten! -->
"""

class XmlFormatter(object):
    """
    Formats Node hierarchy into XML output that looks like Visual Studio's
    native format.
    """

    def __init__(self, paths_info):
        self.expr_formatter = VSExprFormatter(paths_info)

    def format(self, node):
        """
        Formats given node as an XML document and returns the document as a
        string.
        """
        return XML_HEADER + self._format_node(node, "")

    def _format_node(self, n, indent):
        s = "%s<%s" % (indent, n.name)
        for key, value in n.attrs.iteritems():
            s += ' %s=%s' % (key, quoteattr(self._format_value(value)))
        if n.children:
            assert not n.text, "nodes with both text and children not implemented"
            s += ">\n"
            subindent = indent + "  "
            for key, value in n.children:
                if isinstance(value, Node):
                    assert key == value.name
                    s += self._format_node(value, subindent)
                else:
                    v = escape(self._format_value(value))
                    if v:
                        s += "%s<%s>%s</%s>\n" % (subindent, key, v, key)
                    # else: empty value, don't write that

            s += "%s</%s>\n" % (indent, n.name)
        elif n.text:
            s += ">%s</%s>\n" % (n.text, n.name)
        else:
            s += " />\n"
        return s

    def _format_value(self, val):
        if isinstance(val, bkl.expr.Expr):
            s = self.expr_formatter.format(val)
        elif isinstance(val, types.BooleanType):
            s = "true" if val else "false"
        elif isinstance(val, types.ListType):
            s = ";".join(self._format_value(x) for x in val)
        else:
            s = str(val)
        return s


class VSProjectBase(object):
    """
    Base class for all Visual Studio projects.

    To be used by code that interfaces VS toolsets.
    """

    #: Version of the project.
    #: Uses the same format as toolsets name, so the returned value is a
    #: number, e.g. 2010.
    version = None

    #: Name of the project. Typically basename of the project file.
    name = None

    #: GUID of the project.
    guid = None

    #: Filename of the project, as :class:`bkl.expr.Expr`."""
    projectfile = None

    #: List of dependencies of this project, as names."""
    dependencies = []
