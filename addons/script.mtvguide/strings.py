#
#      Copyright (C) 2014 Krzysztof Cebulski
#      Copyright (C) 2013 Szakalit
#
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
import xbmcaddon, xbmc
import traceback, sys

ADDON_ID            = 'script.mtvguide'
RSS_FILE            = 'http://mods-kodi.pl/infusions/kodi_info/kodi_info.txt'
M_TVGUIDE_SUPPORT   = 'http://mods-kodi.pl/m-tvguide/support2018/'
ADDON               = xbmcaddon.Addon(id = ADDON_ID)
ADDON_PATH          = ADDON.getAddonInfo('path')
ADDON_CIDUPDATED    = False    #zabezpieczenie przed ponownym updatem cidow
ADDON_AUTOSTART     = False    #zabezpieczenie przed ponownym uruchomieniem wtyczki
FORCE_ADD_LOG_DEBUG = True     #True - Logowanie nawet jezeli wylaczone debugowanie w XBMC
global M_TVGUIDE_CLOSING
M_TVGUIDE_CLOSING   = False

KODI_VERSION        = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])

RSS_MESSAGE = 30504
NO_DESCRIPTION = 30000
NO_CATEGORY = 30164
CALCULATING_REMAINING_TIME = 30002
TIME_LEFT = 30003
BACKGROUND_UPDATE_IN_PROGRESS = 30004

NO_STREAM_AVAILABLE_TITLE = 30100
NO_STREAM_AVAILABLE_LINE1 = 30101
NO_STREAM_AVAILABLE_LINE2 = 30102

CLEAR_CACHE = 30104
CLEAR_NOTIFICATIONS = 30108
CLEAR_DB = 30950
DONE = 30105
DONE_DB = 30951

DB_DELETED = 30955

LOAD_ERROR_TITLE = 30150
LOAD_ERROR_LINE1 = 30151
LOAD_ERROR_LINE2 = 30152
CONFIGURATION_ERROR_LINE2 = 30153
LOAD_NOT_CRITICAL_ERROR = 30160
LOAD_CRITICAL_ERROR = 30161

SKIN_ERROR_LINE1 = 30154
SKIN_ERROR_LINE2 = 30155
SKIN_ERROR_LINE3 = 30156
SKIN_ERROR_LINE4 = 30149

NOTIFICATION_5_MINS = 30200
NOTIFICATION_NOW = 30201
NOTIFICATION_POPUP_NAME = 30202
NOTIFICATION_POPUP_QUESTION = 30203
NOTIFICATION_CANCEL = 30204

RECORDED_FILE_POPUP = 310012
RECORDED_FILE_QUESTION = 310013
RECORD_PROGRAM_STRING = 69039
RECORD_PROGRAM_CANCEL_STRING = 30303

WATCH_CHANNEL = 30300
REMIND_PROGRAM = 30301
DONT_REMIND_PROGRAM = 30302
CHOOSE_STRM_FILE = 30304
REMOVE_STRM_FILE = 30306

PREVIEW_STREAM = 30604
STOP_PREVIEW = 30607

WEEBTV_WEBTV_MISSING_1 = 30802
WEEBTV_WEBTV_MISSING_2 = 30803
WEEBTV_WEBTV_MISSING_3 = 30804

SERVICE_ERROR = 57002
SERVICE_NO_PREMIUM = 57039
SERVICE_LOGIN_INCORRECT = 57048

DATABASE_SCHEMA_ERROR_1 = 30157
DATABASE_SCHEMA_ERROR_2 = 30158
DATABASE_SCHEMA_ERROR_3 = 30159

#Controls ID
C_MAIN_SERVICE_NAME = 4918  
C_MAIN_CHAN_NAME = 4919     #nazwa kanalu
C_MAIN_TITLE = 4920         #nazwa programu telewizyjnego
C_MAIN_TIME = 4921          #godziny trwania progrmay
C_MAIN_DESCRIPTION = 4922   #opis programu tv
C_MAIN_IMAGE = 4923         #obraz programu
C_MAIN_LOGO = 4924          #logo programu
C_MAIN_LIVE = 4944          #na zywo
C_PROGRAM_SLIDER = 4998     #slider dla postepu programu
C_PROGRAM_PROGRESS = 4999   #postep programu w info i vosd

C_PROGRAM_EPISODE  = 4925   #odcinek
C_PROGRAM_CATEGORY = 4926   #kategoria
C_PROGRAM_ACTORS = 4928     #aktorzy
C_PROGRAM_PRODUCTION_DATE = 4929    #data produkcji
C_PROGRAM_DIRECTOR = 4930   #rezyser
C_PROGRAM_AGE_ICON = 4932   #od lat
C_VOSD_SERVICE = 4940       #nazwa serwisu
C_MAIN_CHAN_PLAY = 4952     #kanal odtwarzany
C_MAIN_PROG_PLAY = 4953     #program odtwarzany
C_MAIN_TIME_PLAY = 4954     #czas odtwarzanego programu
C_MAIN_NUMB_PLAY = 4955     #numer odtwarzanego kanalu

C_MAIN_PROGRAM_PROGRESS = 4230  #postep aktualnego programu aktywnego
C_MAIN_PROGRAM_PROGRESS_EPG = 4231  #postep programu wybrangeo w epg 
C_MAIN_CALC_TIME_EPG = 4232      #czas trwania programu w epg

C_MAIN_EPG = 5000

DEBUG = True

def strings(id, replacements = None):
    string = ADDON.getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string

def getStateLabel(control, label_idx, default=0):
    """Pobiera z <label2>1234|5678</label2> na podstawie label_idx odpowiednia wartosc
       Jezeli chcesz uzyc tylko jednej wartosci wpisz tak:  1234|
       Jezeli nie wpiszesz znaku | to label2 zostanie uznane za puste - nie moga byc same cyfry
    """
    try:
        values = control.getLabel2().split("|")
        return int(values[label_idx])
    except Exception:
        pass
    return default

def deb(s):
    try:
        xbmc.log("MTVGUIDE @ " + str(s), xbmc.LOGNOTICE)
    except:
        xbmc.log("MTVGUIDE @ " + str(s.encode('ascii', 'ignore')), xbmc.LOGNOTICE)

def debug(s):
    try:
        try:
            xbmc.log("Debug @ " + str(s), xbmc.LOGNOTICE)
        except:
            xbmc.log("Debug @ " + str(s.encode('ascii', 'ignore')), xbmc.LOGNOTICE)
    except:
        xbmc.log("Debug @ " + str(s.encode('ascii', 'ignore')), xbmc.LOGNOTICE)

def getExceptionString():
    except_string = ''
    try:
        (etype, value, traceback_obj) = sys.exc_info()
        excString = traceback.extract_tb(traceback_obj)
        except_string = ''.join(' %s, \nBacktrace: %s' % (str(value), str(excString)))
    except:
        pass
    return except_string