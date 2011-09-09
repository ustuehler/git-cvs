"""Terminal interface and other UI functions."""

import sys
import time

from cvsgit.i18n import _

class Progress(object):
    """Display progress information.
    """

    def __init__(self):
        self.last_progress = 0
        self.last_message = ''
        self.last_count = None
        self.last_total = None
        self.update_suppressed = False

        if sys.stdout.isatty():
            self.update_interval = 1
            self.update = self.update_tty
            self.finish = self.finish_tty
        else:
            self.update_interval = 30
            self.update = self.update_dumb
            self.finish = self.finish_dumb

    def __enter__(self):
        pass

    def __exit__(self, exception_type, value, traceback):
        if not exception_type is KeyboardInterrupt:
            self.finish()
        return False

    def __call__(self, message, count=None, total=None):
        if message != self.last_message or \
                time.time() - self.last_progress > self.update_interval:
            self.last_progress = time.time()
            self.update(message, count, total)
            self.update_suppressed = False
        else:
            self.update_suppressed = True
        self.last_message = message
        self.last_count = count
        self.last_total = total

    def update_tty(self, message, count, total):
        sys.stdout.write('\r' + (' ' * len(self.last_message)) + '\r')
        if count == None:
            sys.stdout.write('%s...' % message)
        elif total == None:
            sys.stdout.write('%s: %d' % (message, count))
        elif count == total:
            sys.stdout.write('%s: %s (%d/%d)' % \
                (message, _('done.'), count, total))
        else:
            sys.stdout.write('%s: %3.0f%% (%d/%d)' % \
                (message, count * 100.0 / total, count, total))
        sys.stdout.flush()

    def finish_tty(self):
        if self.update_suppressed:
            self.update_tty(self.last_message, self.last_count, self.last_total)
            self.update_suppressed = False
        sys.stdout.write('\n')

    def update_dumb(self, message, count, total):
        if count == None:
            sys.stdout.write('%s...\n' % message)
        elif total == None:
            sys.stdout.write('%s: %d\n' % (message, count))
        elif count == total:
            sys.stdout.write('%s: %s (%d/%d)\n' % \
                (message, _('done.'), count, total))
        else:
            sys.stdout.write('%s: %3.0f%% (%d/%d)\n' % \
                (message, count * 100.0 / total, count, total))

    def finish_dumb(self):
        if self.update_suppressed:
            self.update_dumb(self.last_message, self.last_count, self.last_total)
            self.update_suppressed = False

class NoProgress(object):
    """Behaves like Progress but does nothing.
    """

    def __enter__(self):
        pass

    def __exit__(self, exception_type, value, traceback):
        return False

    def __call__(self, message, count=None, total=None):
        pass
