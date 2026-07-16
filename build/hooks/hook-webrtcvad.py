"""PyInstaller hook for the actively maintained webrtcvad-wheels package.

The package exposes the import name ``webrtcvad`` but its distribution metadata
is named ``webrtcvad-wheels``.  The upstream contributed hook assumes the old
``webrtcvad`` distribution and therefore fails before analysis can finish.
"""

from PyInstaller.utils.hooks import copy_metadata


datas = copy_metadata("webrtcvad-wheels")
hiddenimports = ["_webrtcvad"]
