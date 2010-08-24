"""Sub-command handling logic for CVSGit."""

import os
import string
import textwrap
from optparse import OptionParser

class Cmd(object):
    """Abstract base class for commands."""

    def __init__(self):
        # Parse the __doc__ string of this command class. This string
        # must contain three elements: a one-line summary, a short
        # usage help and a long description.  The order is fixed.
        docitems = self.__doc__.split('\n\n', 2)
        if len(docitems) != 3:
            raise RuntimeError, \
                'Not enough elements in __doc__ string of %s' % \
                self.__class__
        self.summary, self.usage, self.description = docitems
        self.summary = string.join(textwrap.dedent(self.summary).
                                   splitlines())
        self.usage = textwrap.dedent(self.usage)
        self.description = textwrap.dedent(self.description).rstrip()

        # For convenience, run the command immediately with arguments
        # taken from sys.argv if the command's module  is __main__.
        if self.__module__ == '__main__':
            import sys
            self.main(sys.argv)


    def main(self, argv):
        self.option_parser = OptionParser(
            prog=os.path.basename(argv[0]),
            description=self.description)

        self.initialize_options()
        self.options, self.args = self.option_parser.parse_args(argv[1:])
        self.finalize_options()
        self.run()

    def usage_error(self, msg):
        self.option_parser.error(msg)

    def initialize_options(self):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__

    def finalize_options(self):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__

    def run(self, *args):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__
