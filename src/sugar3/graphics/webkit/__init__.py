import os

if os.environ.get('SUGAR_USE_WEBKIT1'):
    from sugar3.graphics.webkit.webkit1 import WebView, LoadEvent
else:
    from sugar3.graphics.webkit.webkit2 import WebView, LoadEvent
