#
#      Copyright (C) 2014 Krzysztof Cebulski
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import xbmcaddon
import xbmc
import source
from strings import *

class Service(object):
    def __init__(self):
        self.database = source.Database()
        self.database.initialize(self.onInit)

    def onInit(self, success):
        if success:
            self.database.updateChannelAndProgramListCaches(self.onCachesUpdated)
        else:
            self.database.close()

    def onCachesUpdated(self):
        self.database.close(None)

try:
    global ADDON_AUTOSTART
    ADDON = xbmcaddon.Addon(id = ADDON_ID)

    if ADDON_AUTOSTART == False:
        ADDON_AUTOSTART = True
        if ADDON.getSetting('autostart_mtvguide') == 'true' and xbmc.getCondVisibility('System.HasAddon(%s)' % ADDON_ID):
            xbmc.executebuiltin('RunAddon(%s)' % ADDON_ID)

except source.SourceNotConfiguredException:
    pass  # ignore
except Exception, ex:
    deb('[%s] Uncaugt exception in service.py: %s' % (ADDON_ID, getExceptionString()))
