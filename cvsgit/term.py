"""Terminal interface and other UI functions."""

import sys
import time

from cvsgit.i18n import _

class Progress(object):
    """Display progress information.
    """

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.last_progress = 0

    def __call__(self, message, count, total):
        if not self.enabled:
            return
        if count == 0 or count == total or \
           time.time() - self.last_progress > 1:
            if count == total:
                print '\r%s: %s (%d/%d)' % \
                    (message, _('done.'), count, total)
            else:
                print '\r%s: %3.0f%% (%d/%d)' % \
                    (message, count * 100.0 / total, count, total),
            sys.stdout.flush()
            self.last_progress = time.time()
