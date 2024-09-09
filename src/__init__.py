import sys
import threading
import time
from pathlib import Path

import wx
import wx.aui

from .plugin import Plugin, Meta

plugin = Plugin()
plugin.register()

icon_ = Path(__file__) / "icon-24x24.png"


def check_for_button():
    # From Miles McCoo's blog
    # https://kicad.mmccoo.com/2017/03/05/adding-your-own-command-buttons-to-the-pcbnew-gui/
    def find_pcbnew_window():
        windows = wx.GetTopLevelWindows()
        pcbneww = [w for w in windows if "pcbnew" in w.GetTitle().lower()]
        if len(pcbneww) != 1:
            return None
        return pcbneww[0]

    def callback(_):
        plugin.Run()

    while not wx.GetApp():
        time.sleep(1)
    bm = wx.Bitmap(icon_.as_posix(), wx.BITMAP_TYPE_PNG)
    button_wx_item_id = 0

    from pcbnew import ID_H_TOOLBAR

    while True:
        time.sleep(1)
        pcbnew_window = find_pcbnew_window()
        if not pcbnew_window:
            continue

        top_tb = pcbnew_window.FindWindowById(ID_H_TOOLBAR)
        if button_wx_item_id == 0 or not top_tb.FindTool(button_wx_item_id):
            top_tb.AddSeparator()
            button_wx_item_id = wx.NewId()
            top_tb.AddTool(
                button_wx_item_id,
                Meta.toolname,
                bm,
                Meta.short_description,
                wx.ITEM_NORMAL,
            )
            top_tb.Bind(wx.EVT_TOOL, callback, id=button_wx_item_id)
            top_tb.Realize()


# Add a button the hacky way if plugin button is not supported
# in pcbnew, unless this is linux.
if not plugin.pcbnew_icon_support and not sys.platform.startswith("linux"):
    t = threading.Thread(target=check_for_button)
    t.daemon = True
    t.start()
