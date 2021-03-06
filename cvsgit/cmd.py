"""Sub-command logic for git-cvs."""

import os
import string
import sys
import textwrap
from optparse import OptionParser
from cvsgit.i18n import _

class Cmd(object):
    """Abstract base class for conduit commands.
    """

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

    def _main(self, argv):
        self.option_parser = OptionParser(
            prog=os.path.basename(argv[0]),
            description=self.description,
            usage=self.usage,
            add_help_option=False)

        # Turn off GNU-style mix of arguments and options.  We have
        # subcommands that accept --help, so the main command should
        # not interpret --help after a subcommand name.
        self.option_parser.allow_interspersed_args = False

        self.add_option('--help', action='help', help=\
            _("Show this help and exit."))

        self.initialize_options()
        self.options, self.args = self.option_parser.parse_args(argv[1:])
        self.finalize_options()
        sys.exit(self.run())

    def eval(self, *args):
        try:
            prog = self.__class__.__name__
            self.main([prog] + list(args))
        except SystemExit, e:
            if e.code is None or e.code == 0:
                return 0
            else:
                return e.code

    def main(self, argv):
        try:
            self._main(argv)
        except KeyboardInterrupt:
            # In good old tradition: 128 + signal number (SIGINT=2)
            sys.exit(128 + 2)

    def add_option(self, *args, **kwargs):
        return self.option_parser.add_option(*args, **kwargs)

    def usage_error(self, msg):
        self.option_parser.error(msg)

    def warn(self, msg):
        sys.stderr.write(_('%s: warning: %s\n') % (self.option_parser.prog, msg))

    def error(self, msg):
        sys.stderr.write(_('%s: error: %s\n') % (self.option_parser.prog, msg))

    def fatal(self, msg):
        sys.stderr.write(_('%s: fatal: %s\n') % (self.option_parser.prog, msg))
        sys.exit(1)

    def initialize_options(self):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__

    def finalize_options(self):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__

    def run(self, *args):
        raise RuntimeError, \
            'abstract method -- subclass %s must override' % self.__class__
