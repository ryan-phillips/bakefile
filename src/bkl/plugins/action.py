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
Target for running arbitrary scripts.
"""

from bkl.api import TargetType, Property, BuildNode
from bkl.vartypes import *
from bkl.expr import add_prefix


class ActionTargetType(TargetType):
    """
    Custom action script.

    *Action* targets execute arbitrary commands. They can be used to do various
    tasks that don't fit the model of compiling or creating files, such as
    packaging files, installing, uploading, running tests and so on.

    Actions are currently only supported by makefile-based toolsets.

    .. code-block:: bkl

       action osx-bundle
       {
         deps = test;
         commands = "mkdir -p Test.app/Contents/MacOS"
                    "cp -f test Test.app/Contents/MacOS/test"
                    ;
       }
    """
    name = "action"

    # TODO: add ability to specify action's output files (?)

    properties = [
            Property("commands",
                 type=ListType(StringType()),
                 default=[],
                 inheritable=False,
                 doc="List of commands to run."),
        ]

    def get_build_subgraph(self, toolset, target):
        # prefix each line with @ so that make doesn't output the commands:
        cmds = add_prefix("@", target["commands"]).items
        node = BuildNode(commands=cmds, name=target["id"])
        return [node]