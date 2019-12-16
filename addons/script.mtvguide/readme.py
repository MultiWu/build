#      Copyright (C) 2018 Mariusz Brychcy
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import sys, os
from strings import *
which = sys.argv[1]

if which == "readme":
    path = os.path.join(ADDON.getAddonInfo('path'), 'readme.xml')
f = xbmcvfs.File(path,"rb")
data = f.read()
dialog = xbmcgui.Dialog()
dialog.textviewer(strings(90003).encode('utf-8'), data)
