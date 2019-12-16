#
#      Copyright (C) 2018 Mariusz Brychcy
#      Copyright (C) 2016 Andrzej Mleczko
#      Copyright (C) 2014 Krzysztof Cebulski
#      Copyright (C) 2013 Szakalit
#
#      Some implementation are modificated and taken from "Fullscreen TVGuide" - thank you very much primaeval!
#
#      Copyright (C) 2013 Tommy Winther

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
import re, os, datetime, time, platform, threading
import xbmc, xbmcgui
import ConfigParser
import source as src
from notification import Notification
from strings import *
import strings as strings2
import streaming
import playService
import xbmcvfs
import requests
import json
from vosd import VideoOSD
from recordService import RecordService
from skins import Skin
from source import Program, Channel

MODE_EPG = 'EPG'
MODE_TV = 'TV'

ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_UP = 3
ACTION_DOWN = 4
ACTION_PAGE_UP = 5
ACTION_PAGE_DOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_SHOW_INFO = 11
ACTION_STOP = 13
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15

ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_MOUSE_MIDDLE_CLICK = 102
ACTION_MOUSE_WHEEL_UP = 104
ACTION_MOUSE_WHEEL_DOWN = 105
ACTION_MOUSE_MOVE = 107

KEY_NAV_BACK = 92
KEY_CONTEXT_MENU = 117
KEY_HOME = 159
KEY_END = 160

KEY_CODEC_INFO = 0

config = ConfigParser.RawConfigParser()
config.read(os.path.join(Skin.getSkinPath(), 'settings.ini'))
ini_chan = config.getint("Skin", "CHANNELS_PER_PAGE")
ini_info = config.getboolean("Skin", "USE_INFO_DIALOG")


try:
    skin_separate_category = config.getboolean("Skin", "program_category_separated")
except:
    skin_separate_category = False
try:
    skin_separate_episode = config.getboolean("Skin", "program_episode_separated")
except:
    skin_separate_episode = False
try:
    skin_separate_allowed_age_icon = config.getboolean("Skin", "program_allowed_age_icon")
except:
    skin_separate_allowed_age_icon = False
try:
    skin_separate_director = config.getboolean("Skin", "program_director_separated")
except:
    skin_separate_director = False
try:
    skin_separate_year_of_production = config.getboolean("Skin", "program_year_of_production_separated")
except:
    skin_separate_year_of_production = False
try:
    skin_separate_program_progress = config.getboolean("Skin", "program_show_progress_bar")
except:
    skin_separate_program_progress = False
try:
    skin_separate_program_progress_epg = config.getboolean("Skin", "program_show_progress_bar_epg")
except:
    skin_separate_program_progress_epg = False
try:
    skin_separate_program_actors = config.getboolean("Skin", "program_show_actors")
except:
    skin_separate_program_actors = False
try:
    skin_resolution = config.getboolean("Skin", "resolution")
except:
    skin_resolution = '720p'
try:
    cell_height = config.get("Skin", "cell_height")
except:
    cell_height = ''
try:
    cell_width = config.get("Skin", "cell_width")
except:
    cell_width = ''
try:
    skin_font = config.get("Skin", "font")
except:
    skin_font = 'NoFont'
try:
    skin_font_colour = config.get("Skin", "font_colour")
except:
    skin_font_colour = ''
try:
    skin_font_focused_colour = config.get("Skin", "font_focused_colour")
except:
    skin_font_focused_colour = ''

try:
     KEY_INFO = int(ADDON.getSetting('info_key'))
except:
     KEY_INFO = 0
try:
     KEY_STOP = int(ADDON.getSetting('stop_key'))
except:
     KEY_STOP = 0
try:
     KEY_PP = int(ADDON.getSetting('pp_key'))
except:
     KEY_PP = 0
try:
     KEY_PM = int(ADDON.getSetting('pm_key'))
except:
     KEY_PM = 0
try:
     KEY_VOL_UP = int(ADDON.getSetting('volume_up_key'))
except:
     KEY_VOL_UP = -1
try:
     KEY_VOL_DOWN = int(ADDON.getSetting('volume_down_key'))
except:
     KEY_VOL_DOWN = -1
try:
     KEY_HOME2 = int(ADDON.getSetting('home_key'))
except:
     KEY_HOME2 = 0
try:
     KEY_CONTEXT = int(ADDON.getSetting('context_key'))
except:
     KEY_CONTEXT = -1
try:
     KEY_RECORD = int(ADDON.getSetting('record_key'))
except:
     KEY_RECORD = -1
try:
     KEY_LIST = int(ADDON.getSetting('list_key'))
except:
     KEY_LIST = -1
try:
     KEY_SWITCH_TO_LAST = int(ADDON.getSetting('switch_to_last_key'))
except:
     KEY_SWITCH_TO_LAST = -1


CHANNELS_PER_PAGE = ini_chan

HALF_HOUR = datetime.timedelta(minutes = 30)
AUTO_OSD = 666
REFRESH_STREAMS_TIME = 14400

PREDEFINED_CATEGORIES = [strings(30988).encode('utf-8', 'replace'),"Lang: BE", "Lang: CZ", "Lang: DE", "Lang: DK", "Lang: FR", "Lang: HR", "Lang: NO", "Lang: PL", "Lang: SE", "Lang: SRB", "Lang: UK", "Lang: US"]

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'', label)
    label = re.sub(r"\[/?COLOR.*?\]",'', label)
    label = re.sub(r"\[/?CAPITALIZE.*?\]",'', label)
    label = re.sub(r"\(",'', label)
    label = re.sub(r"\)",'', label)
    label = re.sub(r"\s\$ADDON\[script.mtvguide.*?\]",'', label)
    return label

def replace_formatting(label):
    label = re.sub(r"\s\$ADDON\[script.mtvguide.*?\]\.",'', label)
    label = re.sub(r"\$ADDON\[script.mtvguide.*?\]",'[B]N/A', label)
    return label

def timedelta_total_seconds(timedelta):
    return (
        timedelta.microseconds + 0.0 +
        (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6

class Point(object):
    def __init__(self):
        self.x = self.y = 0

    def __repr__(self):
        return 'Point(x=%d, y=%d)' % (self.x, self.y)

class EPGView(object):
    def __init__(self):
        self.top = self.left = self.right = self.bottom = self.width = self.cellHeight = 0

class ControlAndProgram(object):
    def __init__(self, control, program):
        self.control = control
        self.program = program

class Event:
    def __init__(self):
        self.handlers = set()

    def handle(self, handler):
        self.handlers.add(handler)
        return self

    def unhandle(self, handler):
        try:
            self.handlers.remove(handler)
        except:
            raise ValueError("Handler is not handling this event, so cannot unhandle it.")
        return self

    def fire(self, *args, **kargs):
        for handler in self.handlers:
            handler(*args, **kargs)

    def getHandlerCount(self):
        return len(self.handlers)

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__  = getHandlerCount

class VideoPlayerStateChange(xbmc.Player):

    def __init__(self, *args, **kwargs):
        deb ( "################ Starting control VideoPlayer events" )
        self.playerStateChanged = Event()
        self.updatePositionTimerData = {}
        self.recordedFilesPositions = {}
        self.updatePositionTimer = None

    def setPlaylistPositionFile(self, recordedFilesPositions):
        self.recordedFilesPlaylistPositions = recordedFilesPositions

    def stopplaying(self):
        self.updatePositionTimerData['stop'] = True
        self.Stop()

    def onStateChange(self, state):
        self.playerStateChanged(state)

    def onPlayBackPaused(self):
        deb ( "################ Im paused" )
        #self.playerStateChanged("Paused")
        #threading.Timer(0.3, self.stopplaying).start()

    def onPlayBackResumed(self):
        deb ( "################ Im Resumed" )
        #self.onStateChange("Resumed")

    def onPlayBackStarted(self):
        deb ( "################ Playback Started" )
        self.updatePositionTimerData['stop'] = True
        self.onStateChange("Started")
        try:
            playedFile = xbmc.Player().getPlayingFile()
            if os.path.isfile(playedFile):
                try:
                    playlistFileName = re.sub('_part_\d*.mpeg', '.mpeg', playedFile)
                    currentPositionInPlaylist = int(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition())
                    self.recordedFilesPlaylistPositions[playlistFileName] = currentPositionInPlaylist
                    deb('onPlayBackStarted updating playlist position to: %d file: %s' % (currentPositionInPlaylist, playlistFileName))
                except:
                    pass
                try:
                    seek = int(self.recordedFilesPositions[playedFile])
                    deb('onPlayBackStarted seeking file: %s, for %d seconds' % (playedFile, seek))
                    time.sleep(1)
                    xbmc.Player().seekTime(seek)
                except:
                    pass
                self.updatePositionTimerData = {'filename' : playedFile, 'stop' : False}
                self.updatePositionTimer = threading.Timer(10, self.updatePosition, [self.updatePositionTimerData])
                self.updatePositionTimer.start()
        except:
            pass

    def onPlayBackEnded(self):
        xbmc.sleep(100)
        deb ("################# Playback Ended")
        self.updatePositionTimerData['stop'] = True
        self.onStateChange("Ended")

    def onPlayBackStopped(self):
        xbmc.sleep(100)
        deb( "################# Playback Stopped")
        self.updatePositionTimerData['stop'] = True
        self.onStateChange("Stopped")

    def updatePosition(self, updatePositionTimerData):
        try:
            fileName = updatePositionTimerData['filename']
            while updatePositionTimerData['stop'] == False:
                self.recordedFilesPositions[fileName] = xbmc.Player().getTime()
                for sleepTime in range(5):
                    if updatePositionTimerData['stop'] == True:
                        break
                    time.sleep(1)
        except:
            pass

    def close(self):
        self.updatePositionTimerData['stop'] = True
        if self.updatePositionTimer is not None:
            self.updatePositionTimer.cancel()

class mTVGuide(xbmcgui.WindowXML):
    C_MAIN_DATE = 4000

    C_MAIN_TIMEBAR = 4100
    C_MAIN_LOADING = 4200
    C_MAIN_LOADING_BACKGROUND = 4199
    C_MAIN_LOADING_PROGRESS = 4201
    C_MAIN_LOADING_TIME_LEFT = 4202
    C_MAIN_LOADING_CANCEL = 4203
    C_MAIN_MOUSEPANEL_CONTROLS = 4300
    C_MAIN_MOUSEPANEL_HOME = 4301
    C_MAIN_MOUSEPANEL_EPG_PAGE_LEFT = 4302
    C_MAIN_MOUSEPANEL_EPG_PAGE_UP = 4303
    C_MAIN_MOUSEPANEL_EPG_PAGE_DOWN = 4304
    C_MAIN_MOUSEPANEL_EPG_PAGE_RIGHT = 4305
    C_MAIN_MOUSEPANEL_EXIT = 4306
    C_MAIN_MOUSEPANEL_CURSOR_UP = 4307
    C_MAIN_MOUSEPANEL_CURSOR_DOWN = 4308
    C_MAIN_MOUSEPANEL_CURSOR_LEFT = 4309
    C_MAIN_MOUSEPANEL_CURSOR_RIGHT = 4310
    C_MAIN_MOUSEPANEL_SETTINGS = 4311

    C_MAIN_BACKGROUND = 4600
    C_MAIN_EPG = 5000
    C_MAIN_EPG_VIEW_MARKER = 5001
    C_MAIN_INFO = 7000
    C_MAIN_LIVE = 4944

    C_CHANNEL_LABEL_START_INDEX_SHORTCUT = 4010
    C_CHANNEL_IMAGE_START_INDEX_SHORTCUT = 4110
    C_CHANNEL_NUMBER_START_INDEX_SHORTCUT = 4410

    C_CHANNEL_LABEL_START_INDEX = 4510
    C_CHANNEL_IMAGE_START_INDEX = 4210

    def __new__(cls):
        return super(mTVGuide, cls).__new__(cls, 'script-tvguide-main.xml', Skin.getSkinBasePath(), Skin.getSkinName(), defaultRes=skin_resolution)

    def __init__(self):
        deb('')
        deb('###################################################################################')
        deb('')
        deb('m-TVGuide __init__ System: %s, ARH: %s, python: %s, version: %s, kodi: %s' % (platform.system(), platform.machine(), platform.python_version(), ADDON.getAddonInfo('version'), xbmc.getInfoLabel('System.BuildVersion')))
        deb('')
        deb('###################################################################################')
        deb('')
        super(mTVGuide, self).__init__()
        self.database = None
        self.notification = None
        self.infoDialog = None
        self.currentChannel = None
        self.lastChannel = None
        self.program = None
        self.onFocusTimer = None
        self.updateTimebarTimer = None
        self.rssFeed = None
        self.timer = None
        self.initialized = False
        self.redrawingEPG = False
        self.isClosing = False
        self.redrawagain = False
        self.info = False
        self.osd = None
        self.timebar = None
        self.dontBlockOnAction = False
        self.playingRecordedProgram = False
        self.blockInputDueToRedrawing = False
        self.channelIdx = 0
        self.focusPoint = Point()
        self.epgView = EPGView()
        self.a = {}
        self.mode = MODE_EPG
        self.channel_number_input = False
        self.channel_number = ADDON.getSetting('channel.arg')
        self.current_channel_id = None
        self.controlAndProgramList = list()
        self.ignoreMissingControlIds = list()
        self.recordedFilesPlaylistPositions = {}
        self.streamingService = streaming.StreamsService()
        self.playService = playService.PlayService()
        self.recordService = RecordService(self)

        # find nearest half hour
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)

        self.lastKeystroke = datetime.datetime.now()
        self.lastCloseKeystroke = datetime.datetime.now()
        # monitorowanie zmiany stanu odtwarzacza
        threading.Timer(0.3, self.playerstate).start()
        self.autoUpdateCid = ADDON.getSetting('AutoUpdateCid')
        self.ignoreMissingControlIds.append(C_MAIN_CHAN_NAME)
        self.ignoreMissingControlIds.append(C_MAIN_CHAN_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_PROG_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_TIME_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_NUMB_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_CALC_TIME_EPG)

        self.profilePath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
        self.addonPath = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')).decode('utf-8')

        if ADDON.getSetting('refresh_streams') == 'true':
            self.refreshStreamsTimer = threading.Timer(REFRESH_STREAMS_TIME, self.refreshStreamsLoop)
            self.refreshStreamsTimer.start()
        else:
            self.refreshStreamsTimer = None
        self.loadSettings()

        self.cat_index = 0

    def loadSettings(self):
        #Cache textures used to redraw EPG
        self.kolor_filmy_texture         = "default.png"
        self.kolor_seriale_texture       = "default.png"
        self.kolor_informacja_texture    = "default.png"
        self.kolor_rozrywka_texture      = "default.png"
        self.kolor_document_texture      = "default.png"
        self.kolor_dladzieci_texture     = "default.png"
        self.kolor_sport_texture         = "default.png"
        self.kolor_interaktywny_texture  = "default.png"
        self.kolor_default_texture       = "default.png"
        self.focusTexture                = remove_formatting(ADDON.getSetting('color.defaultfocus'))+'.png'

        if ADDON.getSetting('color.Filmy') != '':
            self.kolor_filmy_texture = remove_formatting(ADDON.getSetting('color.Filmy'))+'.png'
        if ADDON.getSetting('color.Seriale') != '':
            self.kolor_seriale_texture = remove_formatting(ADDON.getSetting('color.Seriale'))+'.png'
        if ADDON.getSetting('color.Informacja') != '':
            self.kolor_informacja_texture = remove_formatting(ADDON.getSetting('color.Informacja'))+'.png'
        if ADDON.getSetting('color.Rozrywka') != '':
            self.kolor_rozrywka_texture = remove_formatting(ADDON.getSetting('color.Rozrywka'))+'.png'
        if ADDON.getSetting('color.Dokument') != '':
            self.kolor_document_texture = remove_formatting(ADDON.getSetting('color.Dokument'))+'.png'
        if ADDON.getSetting('color.Dladzieci') != '':
            self.kolor_dladzieci_texture = remove_formatting(ADDON.getSetting('color.Dladzieci'))+'.png'
        if ADDON.getSetting('color.Sport') != '':
            self.kolor_sport_texture = remove_formatting(ADDON.getSetting('color.Sport'))+'.png'
        if ADDON.getSetting('color.InteraktywnyProgramRozrywkowy') != '':
            self.kolor_interaktywny_texture = remove_formatting(ADDON.getSetting('color.InteraktywnyProgramRozrywkowy'))+'.png'
        if ADDON.getSetting('color.default') != '':
            self.kolor_default_texture = remove_formatting(ADDON.getSetting('color.default'))+'.png'

    def createOSD(self, program, urlList):
        try:
            if self.osd:
                try:
                    self.osd.closeOSD()
                except:
                    pass

            osd = Pla(program, self.database, urlList, self)
            self.osd = osd
            osd.doModal()
            osd.close()
            del osd
        except:
            deb('createOSD exception: %s' % getExceptionString())


    def getCategories(self):
        categories = None
        try:
            for serviceName in playService.SERVICES.keys():
                categories = playService.SERVICES[serviceName].getCategoriesFromMap()
                break
        except:
            pass

        if categories is None or categories == {}:
            categories = { 'Movie' : {}, 'Series' : {}, 'Information' : {}, 'Entertainment' : {}, 'Document' : {}, 'Kids' : {}, 'Sport' : {}, 'Interactive Entertainment' : {} }
        #deb('Categories: %s' % str(categories))
        return categories

    def playerstate(self):
        vp = VideoPlayerStateChange()
        vp.setPlaylistPositionFile(self.recordedFilesPlaylistPositions)
        vp.playerStateChanged += self.onPlayerStateChanged
        while not self.isClosing:
            xbmc.sleep(500)
        vp.close()
        return

    def onPlayerStateChanged(self, pstate):
        deb("########### onPlayerStateChanged %s %s" % (pstate, ADDON.getSetting('info.osd')))
        if self.isClosing:
            return
        if (pstate == "Stopped" or pstate == "Ended"):
            if self.playService.isWorking() or xbmc.Player().isPlaying():
                while self.playService.isWorking() == True and not self.isClosing:
                    time.sleep(0.1)
                if self.isClosing:
                    return
                if xbmc.Player().isPlaying():
                    debug('onPlayerStateChanged - was able to recover playback - dont show EPG!')
                    return

            self._showEPG()
            if pstate == "Ended" and self.playingRecordedProgram and self.recordService.isProgramScheduled(self.program) == False:
                time.sleep(0.1)
                if xbmc.Player().isPlaying() == False:
                    deleteFiles = False
                    if ADDON.getSetting('ask_to_delete_watched') == '1':
                        deleteFiles = xbmcgui.Dialog().yesno(heading=strings(69026).encode('utf-8', 'replace'), line1='%s?' % strings(69027).encode('utf-8', 'replace'))
                    elif ADDON.getSetting('ask_to_delete_watched') == '2':
                        deleteFiles = True
                    if deleteFiles == True:
                        self.recordService.removeRecordedProgram(self.program)
        else:
            self._hideEpg()

    def getControl(self, controlId):
        #debug('getControl')
        try:
            return super(mTVGuide, self).getControl(controlId)
        except:
            if controlId in self.ignoreMissingControlIds:
                return None
            if not self.isClosing:
                self.close()
        return None

    def close(self):
        deb('close')
        if not self.isClosing:
            if self.recordService.isRecordOngoing():
                ret = xbmcgui.Dialog().yesno(heading=strings(69000).encode('utf-8', 'replace'), line1='%s' % strings(69011).encode('utf-8', 'replace'), autoclose=60000)
                if ret == False:
                    return
            elif self.recordService.isRecordScheduled():
                ret = xbmcgui.Dialog().yesno(heading=strings(69000).encode('utf-8', 'replace'), line1='%s' % strings(69015).encode('utf-8', 'replace'), autoclose=60000)
                if ret == False:
                    return

            self.isClosing = True
            strings2.M_TVGUIDE_CLOSING = True
            if self.refreshStreamsTimer:
                self.refreshStreamsTimer.cancel()
            if self.timer and self.timer.is_alive():
                self.timer.cancel()

            if self.osd:
                try:
                    self.osd.closeOSD()
                except:
                    pass
            self.playService.close()
            self.recordService.close()
            if self.notification:
                self.notification.close()
            if self.updateTimebarTimer:
                self.updateTimebarTimer.cancel()
            self._clearEpg()
            if self.rssFeed:
                self.rssFeed.close()
            if self.database:
                self.database.close(super(mTVGuide, self).close)
            else:
                super(mTVGuide, self).close()

    def onInit(self):
        deb('onInit')
        if self.initialized:
            # onInit(..) is invoked again by XBMC after a video addon exits after being invoked by XBMC.RunPlugin(..)
            deb("[%s] TVGuide.onInit(..) invoked, but we're already initialized!" % ADDON_ID)
            self.redrawagain = True
            self._showEPG()
            return

        self.initialized = True
        self._hideControl(self.C_MAIN_MOUSEPANEL_CONTROLS)
        self._showControl(self.C_MAIN_EPG, self.C_MAIN_LOADING)
        self._hideControl(self.C_MAIN_LOADING_BACKGROUND)
        self.setControlLabel(self.C_MAIN_LOADING_TIME_LEFT, strings(BACKGROUND_UPDATE_IN_PROGRESS))
        self.setFocusId(self.C_MAIN_LOADING_CANCEL)

        control = self.getControl(self.C_MAIN_EPG_VIEW_MARKER)
        if control:
            left, top = control.getPosition()
            self.focusPoint.x = left
            self.focusPoint.y = top
            self.epgView.left = left
            self.epgView.top = top
            self.epgView.right = left + control.getWidth()
            self.epgView.bottom = top + control.getHeight()
            self.epgView.width = control.getWidth()
            self.epgView.cellHeight = control.getHeight() / CHANNELS_PER_PAGE

        try:
            self.database = src.Database()
        except src.SourceNotConfiguredException:
            self.onSourceNotConfigured()
            self.close()
            return
        self.database.initialize(self.onSourceInitialized, self.isSourceInitializationCancelled)
        self.updateTimebar()


        if ADDON.getSetting('show.time') == "true":
            self.showTime = xbmcgui.ControlLabel(30, 10, 300, 75, '$INFO[System.Time]', '0xFFFFFFFF') 
            self.addControl(self.showTime)
            self.showTime.setVisibleCondition('Player.HasVideo + Control.IsVisible(5000)')

    def AutoPlayByNumber(self):
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes=self.viewStartDate.minute % 30,
                                                 seconds=self.viewStartDate.second)
        channelList = self.database.getChannelList(onlyVisible=True)
        self.channelIdx = int(ADDON.getSetting('autostart_channel_number')) - 1
        channel = Channel(id='', title='', logo='', streamUrl='', visible='', weight='')
        program = Program(channel=channelList[self.channelIdx], title='', startDate='', endDate='', description='', imageLarge='', imageSmall='', categoryA='',categoryB='')
        xbmc.sleep(350)
        self.playChannel(program.channel)

    def AutoPlayLastChannel(self):
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes=self.viewStartDate.minute % 30,
                                                 seconds=self.viewStartDate.second)
        channelList = self.database.getChannelList(onlyVisible=True)
        f = xbmcvfs.File(os.path.join(self.profilePath, 'last_channel.ini'), "r")
        lines = f.read()
        self.channelIdx = int(lines)
        program = Program(channel=channelList[self.channelIdx], title='', startDate='', endDate='', description='', imageLarge='', imageSmall='', categoryA='',categoryB='')
        xbmc.sleep(350)
        self.playChannel(program.channel)

    def Info(self, program):
        deb('Info')
        self.infoDialog = InfoDialog(program)
        self.infoDialog.setChannel(program)
        self.infoDialog.doModal()
        del self.infoDialog
        self.infoDialog = None

    def ExtendedInfo(self, program):
        title = program.title
        match = re.search('(.*?)\([0-9]{4}\)$',title)
        if match:
            program.title = match.group(1).strip()
            program.title = "Movie"
        if program.title == "Movie":
            selection = 0
        elif program.title == "":
            selection = 1
        else:
            selection = xbmcgui.Dialog().select(strings(30359).encode('utf-8', 'replace'),[strings(30357).encode('utf-8', 'replace'), strings(30358).encode('utf-8', 'replace')])
            if selection == -1:
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                return           
        where = ["movie","tv"]
        url = "https://api.themoviedb.org/3/search/%s?query=%s&api_key=d69992ec810d0f414d3de4a2294b8700&include_adult=false&page=1" % (where[selection], title)
        r = requests.get(url)
        data = json.loads(r.content)
        results = data.get('results')
        id = ''
        if results:
            if len(results) > 0:
                names = ["%s (%s)" % (x.get('name') or x.get('title'),x.get('first_air_date') or x.get('release_date')) for x in results]
                what = xbmcgui.Dialog().select(title, names)
                if what > -1:
                    id = results[what].get('id')
                    ttype = results[what].get('media_ttype')
                    if ttype not in ["movie","tv"]:
                        if selection == 0:
                            ttype = "movie"
                        else:
                            ttype = "tv"
                    if ttype == 'movie':
                        xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedinfo,name=%s,id=%s)' % (title.encode('utf-8', 'replace'), id))
                    elif ttype == 'tv':
                        xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,id=%s)' % (program.title.encode('utf-8', 'replace'), id))
                    else:
                        xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                else:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
            else:
                if selection == 0:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30362).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                    search = xbmcgui.Dialog().input(strings(30322).encode('utf-8', 'replace'), program.title.encode('utf-8', 'replace'))
                    if search:
                        xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedinfo,name=%s)' % (search))
                    else:
                        xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                        return
                elif selection == 1:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30363).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                    search = xbmcgui.Dialog().input(strings(30322).encode('utf-8', 'replace'), title.encode('utf-8', 'replace'))
                    if search:
                        xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedtvinfo,name=%s)' % (search))
                    else:
                        xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                        return
                else:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
        else:
            if selection == 0:
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30362).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                search = xbmcgui.Dialog().input(strings(30322).encode('utf-8', 'replace'), program.title.encode('utf-8', 'replace'))
                if search:
                    xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedinfo,name=%s)' % (search))
                else:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                    return
            elif selection == 1:
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30363).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                search = xbmcgui.Dialog().input(strings(30322).encode('utf-8', 'replace'), title.encode('utf-8', 'replace'))
                if search:
                    xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedtvinfo,name=%s)' % (search))
                else:
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))
                    return
            else:
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8', 'replace'), strings(30361).encode('utf-8', 'replace') % title.encode('utf-8', 'replace'))

    def playShortcut(self):
        self.channel_number_input = False
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes=self.viewStartDate.minute % 30, seconds=self.viewStartDate.second)
        channelList = self.database.getChannelList(onlyVisible=True)
        if ADDON.getSetting('channel.shortcut') == 'false':
            for i in range(len(channelList)):
                if self.channel_number == channelList[i].id:
                     self.channelIdx = i
                     break
        else:
            self.channelIdx = (int(self.channel_number) -1)
            self.channel_number = ""
            self.getControl(9999).setLabel(self.channel_number)

        behaviour = int(ADDON.getSetting('channel.shortcut.behaviour'))
        if (self.mode != MODE_EPG) and (behaviour > 0):
            program = Program(channel=channelList[self.channelIdx], title='', startDate=None, endDate=None, description='', categoryA='', categoryB='')
            self.playChannel2(program)
        elif (behaviour == 1) or (behaviour == 1 and self.mode != MODE_EPG):
            self.focusPoint.y = self.epgView.top
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            xbmc.executebuiltin('Action(Select)')
        else:
            self.focusPoint.y = self.epgView.top
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)

    def onAction(self, action):
        if not self.isClosing:
            self.lastKeystroke = datetime.datetime.now()
            if self.mode == MODE_TV:
                self.onActionTVMode(action)
            elif self.mode == MODE_EPG:
                self.onActionEPGMode(action)

        if (ADDON.getSetting('channel.shortcut') != 'false'):
            digit = None
            if not self.channel_number_input:
                code = action.getButtonCode() - 61488
                action_code = action.getId() - 58
                action_code_2 = action.getId() - 140
                if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                    digit = None
                    if (code >= 0 and code <= 9):
                        digit = code
                    elif (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = action_code_2
                    else:
                        digit = action_code
                    self.channel_number_input = True
                    self.channel_number = str(digit)
                    self.getControl(9999).setLabel(self.channel_number)
                    if self.timer and self.timer.is_alive():
                        self.timer.cancel()
                    self.timer = threading.Timer(2, self.playShortcut)
                    self.timer.start()

            if self.channel_number_input:
                if digit == None:
                    code = action.getButtonCode() - 61488
                    action_code = action.getId() - 58
                    action_code_2 = action.getId() - 140
                    if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = None
                        if (code >= 0 and code <= 9):
                            digit = code
                        elif (action_code_2 >= 0 and action_code_2 <= 9):
                            digit = action_code_2
                        else:
                            digit = action_code
                    if digit != None:
                        self.channel_number = "%s%d" % (self.channel_number.strip('_'),digit)
                        self.getControl(9999).setLabel(self.channel_number)
                        if self.timer and self.timer.is_alive():
                            self.timer.cancel()
                        self.timer = threading.Timer(2, self.playShortcut)
                        self.timer.start()


        if (ADDON.getSetting('channel.shortcut') == 'false'):
            digit = None
            if not self.channel_number_input:
                code = action.getButtonCode() - 61488
                action_code = action.getId() - 58
                action_code_2 = action.getId() - 140
                if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                    digit = None
                    if (code >= 0 and code <= 9):
                        digit = code
                    elif (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = action_code_2
                    else:
                        digit = action_code
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
                    return

            if self.channel_number_input:
                if digit == None:
                    code = action.getButtonCode() - 61488
                    action_code = action.getId() - 58
                    action_code_2 = action.getId() - 140
                    if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = None
                        if (code >= 0 and code <= 9):
                            digit = code
                        elif (action_code_2 >= 0 and action_code_2 <= 9):
                            digit = action_code_2
                        else:
                            digit = action_code
                    if digit != None:
                        xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
                        return

    def onActionTVMode(self, action):
        debug('onActionTVMode actId %d, buttonCode %d' % (action.getId(), action.getButtonCode()))
        if action.getId() == ACTION_PAGE_UP:
            self._channelUp()

        elif action.getId() == ACTION_PAGE_DOWN:
            self._channelDown()

        elif action.getId() == KEY_CONTEXT_MENU or action.getButtonCode() == KEY_CONTEXT:
            if not self.playingRecordedProgram:
                self.playService.playNextStream()

        elif action.getId() in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU]:
            self.onRedrawEPG(self.channelIdx, self.viewStartDate, self._getCurrentProgramFocus)

        elif action.getId() == ACTION_STOP or (action.getButtonCode() == KEY_STOP and KEY_STOP != 0):
            self.playService.stopPlayback()


    def onActionEPGMode(self, action):
        debug('onActionEPGMode keyId %d, buttonCode %d' % (action.getId(), action.getButtonCode()))
        if action.getId() in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU]:
            if xbmc.Player().isPlaying() or self.playService.isWorking():
                self.playService.stopPlayback()
            elif action.getButtonCode() != 0 or action.getId() == ACTION_SELECT_ITEM:
                if ADDON.getSetting('exit') == '0':
                    # Ask to close
                    ret = xbmcgui.Dialog().yesno(heading=strings(30963).encode('utf-8', 'replace'), line1='%s?' % strings(30981).encode('utf-8', 'replace'))
                    if ret == False:
                        return
                    elif ret == True:
                        self.close()
                else:
                    # Close by two returns
                    if (datetime.datetime.now() - self.lastCloseKeystroke).seconds < 3:
                        self.close()
                    else:
                        self.lastCloseKeystroke = datetime.datetime.now()
                        xbmcgui.Dialog().notification(strings(30963).encode('utf-8'), strings(30964).encode('utf-8'), time=3000, sound=False)

        elif action.getId() == ACTION_MOUSE_MOVE:
            if ADDON.getSetting('pokazpanel') == 'true':
                self._showControl(self.C_MAIN_MOUSEPANEL_CONTROLS)
            return

        if not self.dontBlockOnAction and self.blockInputDueToRedrawing : #Workaround for occasional gui freeze caused by muliple buttons pressed
            debug('Ignoring action')
            return

        elif action.getId() == ACTION_SHOW_INFO or (action.getButtonCode() == KEY_INFO and KEY_INFO != 0) or (action.getId() == KEY_INFO and KEY_INFO != 0):
            if not ini_info:
                return
            try:
                controlInFocus = self.getFocus()
                program = self._getProgramFromControl(controlInFocus)
                if program is not None:
                    d = xbmcgui.Dialog()
                    list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                    if list == 0:
                        self.Info(program)
                    elif list == 1:
                        self.ExtendedInfo(program)
            except:
                pass
            return

        elif action.getId() == KEY_CONTEXT_MENU or action.getButtonCode() == KEY_CONTEXT or action.getId() == ACTION_MOUSE_RIGHT_CLICK:
            if xbmc.Player().isPlaying():

                if ADDON.getSetting('start_video_minimalized') == 'false' or self.playingRecordedProgram or self.currentChannel is None:
                    xbmc.executebuiltin("Action(FullScreen)")
                self._hideEpg()
                if ADDON.getSetting('info.osd') == "true" and not self.playingRecordedProgram and self.currentChannel is not None:
                    self.createOSD(None, None)
                return

        elif action.getId() == ACTION_STOP or (action.getButtonCode() == KEY_STOP and KEY_STOP != 0):
            self.playService.stopPlayback()

        controlInFocus = None
        currentFocus = self.focusPoint
        try:
            controlInFocus = self.getFocus()
            if controlInFocus in [elem.control for elem in self.controlAndProgramList]:
                (left, top) = controlInFocus.getPosition()
                currentFocus = Point()
                currentFocus.x = left + (controlInFocus.getWidth() / 2)
                currentFocus.y = top + (controlInFocus.getHeight() / 2)
        except Exception:
            control = self._findControlAt(self.focusPoint)
            if control is None and len(self.controlAndProgramList) > 0:
                control = self.controlAndProgramList[0].control
            if control is not None:
                self.setFocus(control)
                if action.getId() == ACTION_MOUSE_WHEEL_UP:
                    pass
                elif action.getId() == ACTION_MOUSE_WHEEL_DOWN:
                    pass
                else:
                    return

        if action.getId() == ACTION_LEFT:
            self._left(currentFocus)
        elif action.getId() == ACTION_RIGHT:
            self._right(currentFocus)
        elif action.getId() == ACTION_UP:
            self._up(currentFocus)
        elif action.getId() == ACTION_DOWN:
            self._down(currentFocus)
        elif action.getId() == ACTION_NEXT_ITEM:
            self._nextDay()
        elif action.getId() == ACTION_PREV_ITEM:
            self._previousDay()
        elif action.getId() == ACTION_PAGE_UP:
            self._moveUp(CHANNELS_PER_PAGE)
        elif action.getId() == ACTION_PAGE_DOWN:
            self._moveDown(CHANNELS_PER_PAGE)
        elif action.getId() == ACTION_MOUSE_WHEEL_UP:
            self._moveUp(scrollEvent = True)
        elif action.getId() == ACTION_MOUSE_WHEEL_DOWN:
            self._moveDown(scrollEvent = True)
        elif action.getId() == KEY_HOME or (action.getButtonCode() == KEY_HOME2 and KEY_HOME2 != 0) or (action.getId() == KEY_HOME2 and KEY_HOME2 != 0):
            self.viewStartDate = datetime.datetime.today()
            self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
            self.onRedrawEPG(0, self.viewStartDate)
        elif action.getId() == KEY_END:
            self.viewStartDate = datetime.datetime.today()
            self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
            self.onRedrawEPG(-1, self.viewStartDate)
        elif (action.getId() in [KEY_CONTEXT_MENU, ACTION_MOUSE_RIGHT_CLICK] or action.getButtonCode() in [KEY_CONTEXT]) and controlInFocus is not None:
            program = self._getProgramFromControl(controlInFocus)
            if program is not None:
                self._showContextMenu(program)
                return
        elif action.getButtonCode() == KEY_RECORD:
            program = self._getProgramFromControl(controlInFocus)
            self.recordProgram(program)
            return

        elif action.getButtonCode() == KEY_LIST:
            program = self._getProgramFromControl(controlInFocus)
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(program.channel)
            elif list == 1:
                self.showNow(program.channel)
            elif list == 2:
                self.showNext(program.channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
            return

        elif action.getId() == ACTION_MOUSE_MIDDLE_CLICK:
            program = self._getProgramFromControl(controlInFocus)
            if ADDON.getSetting('channel.shortcut') == 'false':
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
            else:
                if ADDON.getSetting('channel.shortcut') == 'true':
                    d = xbmcgui.Dialog()
                    number = d.input(strings(30346).encode('utf-8'),type=xbmcgui.INPUT_NUMERIC)
                    if number:
                        self.channel_number = number
                        if self.timer and self.timer.is_alive():
                            self.timer.cancel()
                        self.playShortcut()

        elif action.getButtonCode() == KEY_SWITCH_TO_LAST:
            channel = self.getLastChannel()
            if channel:
                program = self.database.getCurrentProgram(channel)
                if program:
                    deb('Playling last program')
                    self.playChannel2(program)

    def onClick(self, controlId):
        debug('onClick')
        if self.isClosing:
            return
        self.lastKeystroke = datetime.datetime.now()
        channel = None
        if controlId in [self.C_MAIN_LOADING_CANCEL, self.C_MAIN_MOUSEPANEL_EXIT]:
            if ADDON.getSetting('exit') == '0':
                # Ask to close
                if xbmcgui.Dialog().yesno(heading=strings(30963).encode('utf-8', 'replace'), line1='%s?' % strings(30981).encode('utf-8', 'replace')) == True:
                    self.close()
            else:
                self.close()
            return

        if self.isClosing:
            return

        if controlId == self.C_MAIN_MOUSEPANEL_HOME:
            self.viewStartDate = datetime.datetime.today()
            self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_EPG_PAGE_LEFT:
            self.viewStartDate -= datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_EPG_PAGE_UP:
            self._moveUp(count = CHANNELS_PER_PAGE)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_EPG_PAGE_DOWN:
            self._moveDown(count = CHANNELS_PER_PAGE)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_EPG_PAGE_RIGHT:
            self.viewStartDate += datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_CURSOR_UP:
            self._moveUp(scrollEvent = True)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_CURSOR_DOWN:
            self._moveDown(scrollEvent = True)
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_CURSOR_RIGHT:
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_CURSOR_LEFT:
            return
        elif controlId == self.C_MAIN_MOUSEPANEL_SETTINGS:
             xbmcaddon.Addon(id=ADDON_ID).openSettings()
             return
        elif controlId >= 9010 and controlId <= 9021:
            o = controlId - 9010
            try:
                channel = self.a[o]
            except Exception, ex:
                deb('RecordAppImporter Error: %s' % getExceptionString())

        program = self._getProgramFromControl(self.getControl(controlId))
        if channel is not None:
            if not self.playChannel(channel, program):
                result = self.streamingService.detectStream(channel)
                if not result:
                    return
                elif type(result) == str:
                    # one single stream detected, save it and start streaming
                    self.database.setCustomStreamUrl(channel, result)
                    self.playChannel(channel, program)

                else:
                    # multiple matches, let user decide

                    d = ChooseStreamAddonDialog(result)
                    d.doModal()
                    if d.stream is not None:
                        self.database.setCustomStreamUrl(channel, d.stream)
                        self.playChannel(channel, program)
            return

        if program is None:
            return

        if ADDON.getSetting('info.osd') == "true":

            if not self.playChannel2(program):
                result = self.streamingService.detectStream(program.channel)
                if not result:
                    # could not detect stream, show context menu
                    self._showContextMenu(program)
                elif type(result) == str:
                    # one single stream detected, save it and start streaming
                    self.database.setCustomStreamUrl(program.channel, result)
                    self.playChannel2(program)

                else:
                    # multiple matches, let user decide

                    d = ChooseStreamAddonDialog(result)
                    d.doModal()
                    if d.stream is not None:
                        self.database.setCustomStreamUrl(program.channel, d.stream)
                        self.playChannel2(program)

        else:
            if not self.playChannel(program.channel, program):
                result = self.streamingService.detectStream(program.channel)
                if not result:
                    # could not detect stream, show context menu
                    self._showContextMenu(program)
                elif type(result) == str:
                    # one single stream detected, save it and start streaming
                    self.database.setCustomStreamUrl(program.channel, result)
                    self.playChannel(program.channel)

                else:
                    # multiple matches, let user decide

                    d = ChooseStreamAddonDialog(result)
                    d.doModal()
                    if d.stream is not None:
                        self.database.setCustomStreamUrl(program.channel, d.stream)
                        self.playChannel(program.channel)

    def showListing(self, channel):
        programList = self.database.getChannelListing(channel)
        title = channel.title
        d = ProgramListDialog(title, programList, 0)
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNow(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showNext(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == ACTION_SHOW_INFO:
            try:
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:
                    self.Info(programList[index])
                    self.showListing(programList[index].channel)
                elif list == 1:
                    self.ExtendedInfo(programList[index])
                    self.showListing(programList[index].channel)
            except:
                pass
            return
        elif action == KEY_CONTEXT_MENU and xbmc.Player().isPlaying() == False:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def showNow(self, channel):
        programList = self.database.getNowList(channel)
        title = strings(30311).encode('utf-8')

        currentChannel = None
        for programInList in programList:
           if programInList.channel == channel:
              currentChannel = programList.index(programInList)

        d = ProgramListDialog(title, programList, currentChannel)
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == ACTION_SHOW_INFO:
            try:
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:
                    self.Info(programList[index])
                    self.showNow(programList[index].channel)
                elif list == 1:
                    self.ExtendedInfo(programList[index])
                    self.showNow(programList[index].channel)
            except:
                pass
            return
        elif action == KEY_CONTEXT_MENU and xbmc.Player().isPlaying() == False:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def showNext(self, channel):
        programList = self.database.getNextList(channel)
        title = strings(30312).encode('utf-8')

        currentChannel = None
        for programInList in programList:
           if programInList.channel == channel:
              currentChannel = programList.index(programInList)

        d = ProgramListDialog(title, programList, currentChannel)
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_LEFT:
            self.showNow(programList[index].channel)
        elif action == ACTION_RIGHT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == ACTION_SHOW_INFO:
            try:
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:
                    self.Info(programList[index])
                    self.showNext(programList[index].channel)
                elif list == 1:
                    self.ExtendedInfo(programList[index])
                    self.showNext(programList[index].channel)
            except:
                pass
            return
        elif action == KEY_CONTEXT_MENU and xbmc.Player().isPlaying() == False:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def programSearchSelect(self):
        d = xbmcgui.Dialog()
        what = d.select(strings(30315).encode('utf-8'), [strings(30316).encode('utf-8'), strings(30317).encode('utf-8'), strings(30318).encode('utf-8'), strings(30343).encode('utf-8'), strings(30319).encode('utf-8')])
        if what == -1:
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()

        if what == 0:
            self.programSearch()
            self.index = -1
            self.programSearchSelect()

        elif what == 1:
            self.descriptionSearch()
            self.index = -1
            self.programSearchSelect()
        elif what == 2:
            self.categorySearchInput()
            self.index = -1
            self.programSearchSelect()
        elif what == 3:
            self.categorySearch()
            self.index = -1
            self.programSearchSelect()
        elif what == 4:
            self.channelSearch()
            self.index = -1
            self.programSearchSelect()

    def programSearch(self):
        d = xbmcgui.Dialog()
        title = ''
        try:
            controlInFocus = self.getFocus()
            if controlInFocus:
                program = self._getProgramFromControl(controlInFocus)
                if program:
                    title = program.title
        except:
            if self.currentProgram:
                title = self.currentProgram.title
        file_name = os.path.join(self.profilePath, 'title_search.list')
        f = xbmcvfs.File(file_name,"rb")
        searches = sorted(f.read().splitlines())
        f.close()
        actions = [strings(30320).encode('utf-8'), strings(30321).encode('utf-8')] + searches
        action = d.select(strings(30327).encode('utf-8', 'ignore').decode('utf-8') % title, actions)
        if action == -1:
            return
        elif action == 0:
            pass
        elif action == 1:
            which = d.select(strings(30321).encode('utf-8'), searches)
            if which == -1:
                return
            else:
                del searches[which]
                f = xbmcvfs.File(file_name, "wb")
                f.write('\n'.join(searches))
                f.close()
                return
        else:
            title = searches[action-2]
        search = d.input(strings(30322).encode('utf-8'), title)
        if not search:
            return
        searches = list(set([search] + searches))
        f = xbmcvfs.File(file_name, "wb")
        f.write('\n'.join(searches))
        f.close()
        programList = self.database.programSearch(search)
        title = strings(30322).encode('utf-8')
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)


    def descriptionSearch(self):
        d = xbmcgui.Dialog()
        title = ''
        file_name = os.path.join(self.profilePath, 'synopsis_search.list')
        f = xbmcvfs.File(file_name,"rb")
        searches = sorted(f.read().splitlines())
        f.close()
        actions = [strings(30320).encode('utf-8'), strings(30321).encode('utf-8')] + searches
        action = d.select(strings(30328).encode('utf-8'), actions)
        if action == -1:
            return
        elif action == 0:
            pass
        elif action == 1:
            which = d.select(strings(30321).encode('utf-8'), searches)
            if which == -1:
                return
            else:
                del searches[which]
                f = xbmcvfs.File(file_name,"wb")
                f.write('\n'.join(searches))
                f.close()
                return
        else:
            title = searches[action-2]
        search = d.input(strings(30323).encode('utf-8'), title)
        if not search:
            return
        searches = list(set([search] + searches))
        f = xbmcvfs.File(file_name, "wb")
        f.write('\n'.join(searches))
        f.close()
        programList = self.database.descriptionSearch(search)
        title = strings(30322).encode('utf-8')
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def categorySearchInput(self):
        d = xbmcgui.Dialog()
        title = ''
        file_name = os.path.join(self.profilePath, 'category_search.list')
        f = xbmcvfs.File(file_name,"rb")
        searches = sorted(f.read().splitlines())
        f.close()
        actions = [strings(30320).encode('utf-8'), strings(30321).encode('utf-8')] + searches
        action = d.select(strings(30345).encode('utf-8'), actions)
        if action == -1:
            return
        elif action == 0:
            pass
        elif action == 1:
            which = d.select(strings(30321).encode('utf-8'), searches)
            if which == -1:
                return
            else:
                del searches[which]
                f = xbmcvfs.File(file_name,"wb")
                f.write('\n'.join(searches))
                f.close()
                return
        else:
            title = searches[action-2]
        search = d.input(strings(30344).encode('utf-8'), title)
        if not search:
            return
        searches = list(set([search] + searches))
        f = xbmcvfs.File(file_name, "wb")
        f.write('\n'.join(searches))
        f.close()
        programList = self.database.programCategorySearch(search)
        title = strings(30344).encode('utf-8')
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def categorySearch(self):
        d = xbmcgui.Dialog()
        f = xbmcvfs.File(os.path.join(self.profilePath, 'category_count.ini'))
        category_count = [x.split("=",1) for x in f.read().splitlines()]
        f.close()
        categories = []
        for (c,v) in category_count:
            if not self.database.category or self.database.category == "All Channels":
                s = "%s (%s)" % (c,v)
            else:
                s = c
            categories.append(s)
        which = d.select(strings(30324).encode('utf-8'),categories)
        if which == -1:
            return
        category = category_count[which][0]
        programList = self.database.programCategorySearch(category)
        title = "%s" % category
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def channelSearch(self):
        d = xbmcgui.Dialog()
        search = d.input(strings(30326).encode('utf-8'))
        if not search:
            return
        programList = self.database.channelSearch(search)
        title = strings(30326).encode('utf-8')
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def showReminders(self):
        programList = self.database.getNotifications()
        title = (strings(30336).encode('utf-8'))
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def showFullReminders(self):
        programList = self.database.getFullNotifications(int(ADDON.getSetting('listing.days')))
        title = (strings(30336).encode('utf-8'))
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def showFullRecordings(self):
        programList = self.database.getFullRecordings(int(ADDON.getSetting('listing.days')))
        title = (strings(30337).encode('utf-8'))
        d = ProgramListDialog(title, programList, self.currentChannel, ADDON.getSetting('listing.sort.time') == 'true')
        d.doModal()
        index = d.index
        action = d.action
        if action == ACTION_RIGHT:
            self.showNext(programList[index].channel)
        elif action == ACTION_LEFT:
            self.showListing(programList[index].channel)
        elif action == KEY_NAV_BACK:
            self.index = -1
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(programList[index].channel)
            elif list == 1:
                self.showNow(programList[index].channel)
            elif list == 2:
                self.showNext(programList[index].channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
        elif action == KEY_CONTEXT_MENU:
            if index > -1:
                self._showContextMenu(programList[index])
        else:
            if index > -1:
                program = programList[index]
                now = datetime.datetime.now()
                start = program.startDate
                end = program.endDate
                self.playChannel2(program)

    def _showContextMenu(self, program):
        deb('_showContextMenu')
        self._hideControl(self.C_MAIN_MOUSEPANEL_CONTROLS)
        d = PopupMenu(self.database, program, not program.notificationScheduled)
        d.doModal()
        buttonClicked = d.buttonClicked
        new_category = d.category
        del d

        if buttonClicked == PopupMenu.C_POPUP_REMIND:
            if program.notificationScheduled:
                self.notification.removeNotification(program)
            else:
                self.notification.addNotification(program)

            self.onRedrawEPG(self.channelIdx, self.viewStartDate)

        elif buttonClicked == PopupMenu.C_POPUP_CHOOSE_STREAM:
            d = StreamSetupDialog(self.database, program.channel)
            d.doModal()
            del d

        elif buttonClicked == PopupMenu.C_POPUP_PLAY:
            self.playChannel(program.channel)

        elif buttonClicked == PopupMenu.C_POPUP_CHANNELS:
            d = ChannelsMenu(self.database, program.channel)
            d.doModal()
            del d
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)

        elif buttonClicked == PopupMenu.C_POPUP_QUIT:
            self.close()

        elif buttonClicked == PopupMenu.C_POPUP_ADDON_SETTINGS:
            xbmcaddon.Addon(id=ADDON_ID).openSettings()

        elif buttonClicked == PopupMenu.C_POPUP_RECORD:
            self.recordProgram(program)

        elif buttonClicked == PopupMenu.C_POPUP_INFO:
            deb('Info')
            self.infoDialog = InfoDialog(program)
            self.infoDialog.setChannel(program)
            self.infoDialog.doModal()
            del self.infoDialog
            self.infoDialog = None

        elif buttonClicked == PopupMenu.C_POPUP_RECORDINGS:
            xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % ADDON.getSetting('record.folder'))

        elif buttonClicked == PopupMenu.C_POPUP_LISTS:
            d = xbmcgui.Dialog()
            list = d.select(strings(30309).encode('utf-8'), [strings(30310).encode('utf-8'), strings(30311).encode('utf-8'), strings(30312).encode('utf-8'), strings(30336).encode('utf-8'), strings(30337).encode('utf-8'), strings(30315).encode('utf-8')])
            if list < 0:
                self.onRedrawEPG(self.channelIdx, self.viewStartDate)
            if list == 0:
                self.showListing(program.channel)
            elif list == 1:
                self.showNow(program.channel)
            elif list == 2:
                self.showNext(program.channel)
            elif list == 3:
                self.showFullReminders()
            elif list == 4:
                self.showFullRecordings()
            elif list == 5:
                self.programSearchSelect()
            return

        elif buttonClicked == PopupMenu.C_POPUP_CATEGORY:
            self.database.setCategory(new_category)
            ADDON.setSetting('category', new_category)
            self.onRedrawEPG(self.channelIdx == 1, self.viewStartDate)

        elif buttonClicked == PopupMenu.C_POPUP_NUMBER:
            if ADDON.getSetting('channel.shortcut') == 'false':
                xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
            else:
                if ADDON.getSetting('channel.shortcut') == 'true':
                    d = xbmcgui.Dialog()
                    number = d.input(strings(30346).encode('utf-8'),type=xbmcgui.INPUT_NUMERIC)
                    if number:
                        self.channel_number = number
                        if self.timer and self.timer.is_alive():
                            self.timer.cancel()
                        self.playShortcut()

        elif buttonClicked == PopupMenu.C_POPUP_EXTENDED:
            deb('ExtendedInfo')
            self.ExtendedInfo(program)

        elif buttonClicked == PopupMenu.C_POPUP_FAQ:
            xbmcgui.Dialog().textviewer(strings(30994).encode('utf-8'), strings(99996).encode('utf-8'))
            return

    def setFocusId(self, controlId):
        debug('setFocusId')
        control = self.getControl(controlId)
        if control:
            self.setFocus(control)

    def setFocus(self, control):
        #debug('setFocus %d' % control.getId())
        if control in [elem.control for elem in self.controlAndProgramList]:
            (left, top) = control.getPosition()
            if left > self.focusPoint.x or left + control.getWidth() < self.focusPoint.x:
                self.focusPoint.x = left
            self.focusPoint.y = top + (control.getHeight() / 2)
        super(mTVGuide, self).setFocus(control)

    def onFocus(self, controlId):
        #Call filling all program data was delayed, because of Kodi internal error which may lead to Kodi freeze when scrolling
        try:
            if self.onFocusTimer:
                self.onFocusTimer.cancel()
            self.onFocusTimer = threading.Timer(0.20, self.delayedOnFocus, [controlId])
            self.onFocusTimer.start()
        except:
            pass

    def delayedOnFocus(self, controlId):
        debug('onFocus controlId: %s' % controlId)
        try:
            controlInFocus = self.getControl(controlId)
        except Exception, ex:
            deb('onFocus Exception str: %s' % getExceptionString())
            return

        program = self._getProgramFromControl(controlInFocus)
        if program is None:
            return

        self.setControlLabel(C_MAIN_CHAN_NAME, '%s' % (program.channel.title))
        self.setControlLabel(C_MAIN_TITLE, '%s' % (program.title))
        self.setControlLabel(C_MAIN_TIME, '%s - %s' % (self.formatTime(program.startDate), self.formatTime(program.endDate)))

        start_date = datetime.datetime.now() - program.startDate
        end_date = datetime.datetime.now() - program.endDate

        self.setControlLabel(C_MAIN_CALC_TIME_EPG, '%s' % (start_date - end_date))

        if ADDON.getSetting('info.osd') == "false":
            self.setControlLabel(C_MAIN_CHAN_PLAY, '%s' % ("N/A"))
            self.setControlLabel(C_MAIN_PROG_PLAY, '%s' % (strings(55016).encode('utf-8', 'replace')))
            self.setControlLabel(C_MAIN_TIME_PLAY, '%s - %s' % ("N/A", "N/A"))
            self.setControlLabel(C_MAIN_NUMB_PLAY, '%s' % ("-"))

        if program.description:
            description = program.description
        elif program.categoryA:
            category = program.categoryA
        else:
            description = strings(NO_DESCRIPTION)
            category = strings(NO_CATEGORY)

        if skin_separate_category or skin_separate_year_of_production or skin_separate_director or skin_separate_episode or skin_separate_allowed_age_icon or skin_separate_program_progress or skin_separate_program_progress_epg or skin_separate_program_actors:
            #This mean we'll need to parse program description
            descriptionParser = src.ProgramDescriptionParser(description)
            if skin_separate_category:
                category = descriptionParser.extractCategory()
                self.setControlText(C_PROGRAM_CATEGORY, category)
            if skin_separate_year_of_production:
                year = descriptionParser.extractProductionDate()
                self.setControlText(C_PROGRAM_PRODUCTION_DATE, year)
            if skin_separate_director:
                director = descriptionParser.extractDirector()
                self.setControlText(C_PROGRAM_DIRECTOR, director)
            if skin_separate_episode:
                episode = descriptionParser.extractEpisode()
                self.setControlText(C_PROGRAM_EPISODE, episode)
            if skin_separate_allowed_age_icon:
                icon = descriptionParser.extractAllowedAge()
                self.setControlImage(C_PROGRAM_AGE_ICON, icon)
            if skin_separate_program_actors:
                actors = descriptionParser.extractActors()
                self.setControlText(C_PROGRAM_ACTORS, actors)
            if skin_separate_program_progress:
                try:
                    programProgressControl = self.getControl(C_MAIN_PROGRAM_PROGRESS)
                    stdat = time.mktime(self.program.startDate.timetuple())
                    endat = time.mktime(self.program.endDate.timetuple())
                    nodat = time.mktime(datetime.datetime.now().timetuple())
                    percent =  100 -  ((endat - nodat)/ ((endat - stdat)/100))
                    if percent > 0 and percent < 100:
                        programProgressControl.setVisible(True)
                        programProgressControl.setPercent(percent)
                    else:
                        programProgressControl.setVisible(False)
                except:
                    pass
            if skin_separate_program_progress_epg:
                try:
                    programProgressControl = self.getControl(C_MAIN_PROGRAM_PROGRESS_EPG)
                    stdat = time.mktime(program.startDate.timetuple())
                    endat = time.mktime(program.endDate.timetuple())
                    nodat = time.mktime(datetime.datetime.now().timetuple())
                    percent =  100 -  ((endat - nodat)/ ((endat - stdat)/100))
                    if percent > 0 and percent < 100:
                        programProgressControl.setVisible(True)
                        programProgressControl.setPercent(percent)
                    else:
                        programProgressControl.setVisible(False)
                except:
                    pass

            description = descriptionParser.description

        self.setControlText(C_MAIN_DESCRIPTION, description)

        xbmc.sleep(10)
        if program.channel.logo is not None:
            self.setControlImage(C_MAIN_LOGO, program.channel.logo)
        if program.imageSmall is not None:
            self.setControlImage(C_MAIN_IMAGE, program.imageSmall)
        if program.imageSmall is None:
            self.setControlImage(C_MAIN_IMAGE, 'tvguide-logo-epg.png')
        if program.imageLarge == 'live':
            self.setControlImage(C_MAIN_LIVE, 'live.png')
        else:
            self.setControlImage(C_MAIN_LIVE, '')

    def _left(self, currentFocus):
        #debug('_left')
        control = self._findControlOnLeft(currentFocus)
        if control is not None:
            self.setFocus(control)
        elif control is None:
            self.viewStartDate -= datetime.timedelta(hours = 2)
            self.focusPoint.x = self.epgView.right
            self.onRedrawEPG(self.channelIdx, self.viewStartDate, focusFunction=self._findControlOnLeft)

    def _right(self, currentFocus):
        #debug('_right')
        control = self._findControlOnRight(currentFocus)
        if control is not None:
            self.setFocus(control)
        elif control is None:
            self.viewStartDate += datetime.timedelta(hours = 2)
            self.focusPoint.x = self.epgView.left
            self.onRedrawEPG(self.channelIdx, self.viewStartDate, focusFunction=self._findControlOnRight)

    def _up(self, currentFocus):
        #debug('_up')
        currentFocus.x = self.focusPoint.x
        control = self._findControlAbove(currentFocus)
        if control is not None:
            self.setFocus(control)
        elif control is None:
            self.focusPoint.y = self.epgView.bottom
            self.onRedrawEPG(self.channelIdx - CHANNELS_PER_PAGE, self.viewStartDate, focusFunction=self._findControlAbove)

    def _down(self, currentFocus):
        #debug('_down')
        currentFocus.x = self.focusPoint.x
        control = self._findControlBelow(currentFocus)
        if control is not None:
            self.setFocus(control)
        elif control is None:
            self.focusPoint.y = self.epgView.top
            self.onRedrawEPG(self.channelIdx + CHANNELS_PER_PAGE, self.viewStartDate, focusFunction=self._findControlBelow)

    def _nextDay(self):
        deb('_nextDay')
        self.viewStartDate += datetime.timedelta(days = 1)
        self.onRedrawEPG(self.channelIdx, self.viewStartDate)

    def _previousDay(self):
        deb('_previousDay')
        self.viewStartDate -= datetime.timedelta(days = 1)
        self.onRedrawEPG(self.channelIdx, self.viewStartDate)

    def _moveUp(self, count = 1, scrollEvent = False):
        debug('_moveUp')
        if scrollEvent:
            self.dontBlockOnAction = True
            self.onRedrawEPG(self.channelIdx - count, self.viewStartDate)
            self.dontBlockOnAction = False
        else:
            self.focusPoint.y = self.epgView.bottom
            self.onRedrawEPG(self.channelIdx - count, self.viewStartDate, focusFunction = self._findControlAbove)

    def _moveDown(self, count = 1, scrollEvent = False):
        debug('_moveDown')
        if scrollEvent:
            self.dontBlockOnAction = True
            self.onRedrawEPG(self.channelIdx + count, self.viewStartDate)
            self.dontBlockOnAction = False
        else:
            self.focusPoint.y = self.epgView.top
            self.onRedrawEPG(self.channelIdx + count, self.viewStartDate, focusFunction=self._findControlBelow)

    def _channelUp(self):
        channel = self.database.getNextChannel(self.currentChannel)
        self.playChannel2(self.database.getCurrentProgram(channel))

    def _channelDown(self):
        channel = self.database.getPreviousChannel(self.currentChannel)
        self.playChannel2(self.database.getCurrentProgram(channel))

    def playRecordedProgram(self, program):
        self.playingRecordedProgram = False
        recordedProgram = self.recordService.isProgramRecorded(program)
        if recordedProgram is not None:
            diff = program.endDate - datetime.datetime.now()
            diffSeconds = (diff.days * 86400) + diff.seconds
            if diffSeconds <= 0:
                #start recorded program which already ended
                ret = True
            else:
                ret = xbmcgui.Dialog().yesno(heading=strings(RECORDED_FILE_POPUP).encode('utf-8', 'replace'), line1='%s %s?' % (strings(RECORDED_FILE_QUESTION).encode('utf-8', 'replace'), program.title.encode('utf-8', 'replace')), autoclose=60000)
            if ret == True:
                #if ADDON.getSetting('start_video_minimalized') == 'true':
                    #startWindowed = True
                #else:
                    #startWindowed = False
                try:
                    firstFileInPlaylist = recordedProgram[0].getfilename()
                    playlistIndex = int(self.recordedFilesPlaylistPositions[firstFileInPlaylist])
                except:
                    playlistIndex = -1

                deb('playRecordedProgram starting play of recorded program %s from index %d' % (program.title.encode('utf-8', 'replace'), playlistIndex))
                xbmc.Player().play(item=recordedProgram, windowed=False, startpos=playlistIndex)
                self.playingRecordedProgram = True
                return True
        return False

    def updateCurrentChannel(self, channel):
        deb('updateCurrentChannel')
        self.lastChannel = self.currentChannel
        self.currentChannel = channel

        file_name = os.path.join(self.profilePath, 'last_channel.ini')
        f = xbmcvfs.File(file_name, "wb")
        s = "%s" % str(self.database.getCurrentChannelIdx(channel))
        f.write(s)
        f.close()

    def getLastChannel(self):
        return self.lastChannel

    def playChannel2(self, program):
        deb('playChannel2')
        self.program = program
        self.updateCurrentChannel(program.channel)
        if self.playRecordedProgram(program):
            return True

        urlList = self.database.getStreamUrlList(program.channel)
        if len(urlList) > 0:
            #if ADDON.getSetting('start_video_minimalized') == 'false' and xbmc.Player().isPlaying():
                #xbmc.executebuiltin("Action(FullScreen)")
            if ADDON.getSetting('info.osd') == "true":
                self.createOSD(self.program, urlList)
            else:
                self.playService.playUrlList(urlList, resetReconnectCounter=True)
        return len(urlList) > 0

    def playChannel(self, channel, program = None):
        deb('playChannel')
        self.updateCurrentChannel(channel)
        if program is not None:
            self.program = program
            if self.playRecordedProgram(program):
                return True

        urlList = self.database.getStreamUrlList(channel)
        if len(urlList) > 0:
            if ADDON.getSetting('info.osd') == "true":
                self.createOSD(self.program, urlList)
            else:
                self.playService.playUrlList(urlList, resetReconnectCounter=True)
        return len(urlList) > 0

    def recordProgram(self, program):
        deb('recordProgram')
        if self.recordService.recordProgramGui(program):
            self.onRedrawEPG(self.channelIdx, self.viewStartDate)


    def waitForPlayBackStopped(self):
        debug('waitForPlayBackStopped')
        while self.epg.playService.isWorking() == True:
            xbmc.sleep(200)
        while (xbmc.Player().isPlaying() or self.epg.playService.isWorking() == True) and not strings2.M_TVGUIDE_CLOSING and not self.isClosing:
            xbmc.sleep(200)
        self.onPlayBackStopped()

    def _hideEpg(self):
        deb('_hideEpg')
        if ADDON.getSetting('pokazpanel') == 'true':
            self._hideControl(self.C_MAIN_MOUSEPANEL_CONTROLS)
        self._hideControl(self.C_MAIN_EPG)
        self.mode = MODE_TV
        self._clearEpg()

    def _showEPG(self):
        deb('_showEpg')

        #aktualna godzina!
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
        if self.currentChannel is not None:
            currentChannelIndex = self.database.getCurrentChannelIdx(self.currentChannel)
            self.channelIdx = (currentChannelIndex // CHANNELS_PER_PAGE) * CHANNELS_PER_PAGE

        #przerysuj tylko wtedy gdy nie bylo epg! jak jest to nie przerysowuj - nie ustawi sie wtedy na aktualnej godzienie!
        if (self.mode == MODE_TV or self.redrawagain):
            self.onRedrawEPG(self.channelIdx, self.viewStartDate, self._getCurrentProgramFocus) #przerysuj
        if ADDON.getSetting('pokazpanel') == 'true':
            self._showControl(self.C_MAIN_MOUSEPANEL_CONTROLS)


    def disableUnusedChannelControls(self, start_index):
        for idx in range(0, CHANNELS_PER_PAGE):
            self.disableControl(start_index + idx)


    def onRedrawEPG(self, channelStart, startTime, focusFunction = None):
        deb('onRedrawEPG')
        if self.redrawingEPG or (self.database is not None and self.database.updateInProgress) or self.isClosing or strings2.M_TVGUIDE_CLOSING:
            deb('onRedrawEPG - already redrawing')
            return # ignore redraw request while redrawing
        self.redrawingEPG = True
        self.blockInputDueToRedrawing = True
        self.redrawagain = False
        self.mode = MODE_EPG

        if self.onFocusTimer:
            self.onFocusTimer.cancel()
        if self.infoDialog is not None:
            self.infoDialog.close()

        self._showControl(self.C_MAIN_EPG)
        self.updateTimebar(scheduleTimer = False)

        # show Loading screen
        self.setControlLabel(self.C_MAIN_LOADING_TIME_LEFT, strings(CALCULATING_REMAINING_TIME))
        self._showControl(self.C_MAIN_LOADING)
        self.setFocusId(self.C_MAIN_LOADING_CANCEL)
  
        # remove existing controls
        self._clearEpg()
        try:
            self.channelIdx, channels, programs, cacheExpired = self.database.getEPGView(channelStart, startTime, self.onSourceProgressUpdate, clearExistingProgramList = True)
        except src.SourceException:
            self.blockInputDueToRedrawing = False
            debug('onRedrawEPG onEPGLoadError')
            self.onEPGLoadError()
            return

        if cacheExpired == True and ADDON.getSetting('notifications.enabled') == 'true':
            #make sure notifications are scheduled for newly downloaded programs
            self.notification.scheduleNotifications()

        # date and time row
        self.setControlLabel(self.C_MAIN_DATE, self.formatDate(self.viewStartDate))
        for col in range(1, 5):
            self.setControlLabel(4000 + col, self.formatTime(startTime))
            startTime += HALF_HOUR

        if programs is None:
            debug('onRedrawEPG onEPGLoadError2')
            self.onEPGLoadError()
            return

        categories = self.getCategories()

        for program in programs:
            idx = channels.index(program.channel)

            startDelta = program.startDate - self.viewStartDate
            stopDelta = program.endDate - self.viewStartDate

            cellStart = self._secondsToXposition(startDelta.seconds)
            if startDelta.days < 0:
                cellStart = self.epgView.left
            cellWidth = self._secondsToXposition(stopDelta.seconds) - cellStart
            if cellStart + cellWidth > self.epgView.right:
                cellWidth = self.epgView.right - cellStart
            if cellWidth > 1:

                if program.categoryA in categories['Movie']:
                    noFocusTexture = self.kolor_filmy_texture

                elif program.categoryA in categories['Series']:
                    noFocusTexture = self.kolor_seriale_texture

                elif program.categoryA in categories['Information']:
                    noFocusTexture = self.kolor_informacja_texture

                elif program.categoryA in categories['Entertainment']:
                    noFocusTexture = self.kolor_rozrywka_texture

                elif program.categoryA in categories['Document']:
                    noFocusTexture = self.kolor_document_texture

                elif program.categoryA in categories['Kids']:
                    noFocusTexture = self.kolor_dladzieci_texture

                elif program.categoryA in categories['Sport']:
                    noFocusTexture = self.kolor_sport_texture

                elif program.categoryA in categories['Interactive Entertainment']:
                    noFocusTexture = self.kolor_interaktywny_texture
                else:
                    noFocusTexture = self.kolor_default_texture

                if program.notificationScheduled:
                    noFocusTexture = remove_formatting(ADDON.getSetting('color.notification'))+'.png'

                if program.recordingScheduled:
                    noFocusTexture = remove_formatting(ADDON.getSetting('color.recording'))+'.png'


                if cellWidth < 35:
                    title = '' # Text will overflow outside the button if it is too narrow
                else:
                    title = program.title

                control = xbmcgui.ControlButton(
                    cellStart,
                    self.epgView.top + self.epgView.cellHeight * idx,
                    cellWidth - (int(cell_width)),
                    self.epgView.cellHeight - (int(cell_height)),
                    title,
                    noFocusTexture = noFocusTexture,
                    focusTexture = self.focusTexture,
                    font = skin_font,
                    textColor = skin_font_colour,
                    focusedColor = skin_font_focused_colour
                )

                self.controlAndProgramList.append(ControlAndProgram(control, program))
        # add program controls
        if focusFunction is None:
            focusFunction = self._findControlAt
        focusControl = focusFunction(self.focusPoint)
        if focusControl is None:
            focusControl = self._findControlAt(self.focusPoint)
        controls = [elem.control for elem in self.controlAndProgramList]
        self.addControls(controls)
        if focusControl is not None:
            self.setFocus(focusControl)
        self.ignoreMissingControlIds.extend([elem.control.getId() for elem in self.controlAndProgramList])
        if focusControl is None and len(self.controlAndProgramList) > 0:
            self.setFocus(self.controlAndProgramList[0].control)

        self._showControl(self.C_MAIN_LOADING_BACKGROUND)
        self._hideControl(self.C_MAIN_LOADING)
        
        self.blockInputDueToRedrawing = False

        if ADDON.getSetting('channel.shortcut') == 'true':
            channel_index_format = "%%0%sd" % 1
            show_channel_numbers = True
            CHANNEL_LABEL = self.C_CHANNEL_LABEL_START_INDEX_SHORTCUT
            CHANNEL_IMAGE = self.C_CHANNEL_IMAGE_START_INDEX_SHORTCUT
        else:
            show_channel_numbers = False
            CHANNEL_LABEL = self.C_CHANNEL_LABEL_START_INDEX
            CHANNEL_IMAGE = self.C_CHANNEL_IMAGE_START_INDEX

        if ADDON.getSetting('show.logo') == 'true':
            show_channel_logo = True
        else:
            show_channel_logo = False

        # set channel logo or text
        for idx in range(0, CHANNELS_PER_PAGE):
            if idx % 2 == 0 and not self.dontBlockOnAction:
                xbmc.sleep(20) #Fix for ocasional gui freeze during quick scrolling

            if idx >= len(channels):
                # Clear remaining channels
                self.setControlImage(CHANNEL_IMAGE + idx, ' ')
                self.setControlLabel(CHANNEL_LABEL + idx, ' ')
                if show_channel_numbers:
                    self.setControlLabel(self.C_CHANNEL_NUMBER_START_INDEX_SHORTCUT + idx, ' ')

            else:
                channel = channels[idx]
                self.setControlLabel(CHANNEL_LABEL + idx, channel.title)

                if show_channel_numbers:
                    self.setControlLabel(self.C_CHANNEL_NUMBER_START_INDEX_SHORTCUT + idx, channel_index_format % (self.channelIdx + idx + 1))

                if show_channel_logo:
                    if channel.logo is not None:
                        self.setControlImage(CHANNEL_IMAGE + idx, channel.logo)
                    else:
                        self.setControlImage(CHANNEL_IMAGE + idx, ' ')

                    self.a[idx] = channel

        #Redraw timebar
        tmp_control = self.getControl(self.C_MAIN_TIMEBAR)
        if self.timebar:
            self.removeControl(self.timebar)
        self.timebar = xbmcgui.ControlImage(tmp_control.getX(), tmp_control.getY(), tmp_control.getWidth(), tmp_control.getHeight(), os.path.join(Skin.getSkinPath(), 'media', 'tvguide-timebar.png'))
        self.addControl(self.timebar)
        self.updateTimebar()

        self.redrawingEPG = False
        if self.redrawagain:
            debug('onRedrawEPG redrawing again')
            self.redrawagain = False
            self.onRedrawEPG(channelStart, self.viewStartDate, focusFunction)
        debug('onRedrawEPG done')

    def _clearEpg(self):
        deb('_clearEpg')
        if self.timebar:
            self.removeControl(self.timebar)
            self.timebar = None
        controls = [elem.control for elem in self.controlAndProgramList]
        try:
            self.removeControls(controls)
        except:
            debug('_clearEpg failed to delete all controls, deleting one by one')
            for elem in self.controlAndProgramList:
                try:
                    self.removeControl(elem.control)
                except RuntimeError, ex:
                    debug('_clearEpg RuntimeError: %s' % getExceptionString())
                    pass # happens if we try to remove a control that doesn't exist
                except Exception, ex:
                    deb('_clearEpg unhandled exception: %s' % getExceptionString())
        del self.controlAndProgramList[:]
        debug('_clearEpg end')

    def onEPGLoadError(self):
        deb('onEPGLoadError, M_TVGUIDE_CLOSING: %s' % strings2.M_TVGUIDE_CLOSING)
        self.redrawingEPG = False
        self._hideControl(self.C_MAIN_LOADING)
        if not strings2.M_TVGUIDE_CLOSING:
            xbmcgui.Dialog().ok(strings(LOAD_ERROR_TITLE), strings(LOAD_ERROR_LINE1), ADDON.getSetting('m-TVGuide').strip(), strings(LOAD_ERROR_LINE2))
        self.close()

    def onSourceNotConfigured(self):
        deb('onSourceNotConfigured')
        self.redrawingEPG = False
        self._hideControl(self.C_MAIN_LOADING)
        xbmcgui.Dialog().ok(strings(LOAD_ERROR_TITLE), strings(LOAD_ERROR_LINE1), strings(CONFIGURATION_ERROR_LINE2) + '\n' + strings(69036) + ADDON.getSetting('m-TVGuide').strip())
        self.close()

    def isSourceInitializationCancelled(self):
        initialization_cancelled = strings2.M_TVGUIDE_CLOSING or self.isClosing
        deb('isSourceInitializationCancelled: %d' % initialization_cancelled)
        return initialization_cancelled

    def onSourceInitialized(self, success):
        deb('onSourceInitialized')
        if success:
            self.notification = Notification(self.database, ADDON.getAddonInfo('path'), self)
            if ADDON.getSetting('notifications.enabled') == 'true':
                self.notification.scheduleNotifications()
            self.recordService.scheduleAllRecordings()
            self.rssFeed = src.RssFeed(url=RSS_FILE, last_message=self.database.getLastRssDate(), update_date_call=self.database.updateRssDate)
            if strings2.M_TVGUIDE_CLOSING == False:

                if ADDON.getSetting('channel.shortcut') == 'true':
                    self.disableUnusedChannelControls(self.C_CHANNEL_LABEL_START_INDEX)
                    self.disableUnusedChannelControls(self.C_CHANNEL_IMAGE_START_INDEX)
                else:
                    self.disableUnusedChannelControls(self.C_CHANNEL_LABEL_START_INDEX_SHORTCUT)
                    self.disableUnusedChannelControls(self.C_CHANNEL_IMAGE_START_INDEX_SHORTCUT)
                    self.disableUnusedChannelControls(self.C_CHANNEL_NUMBER_START_INDEX_SHORTCUT)

                if ADDON.getSetting('categories.remember') == 'true' and ADDON.getSetting('category') != '':
                    self.database.setCategory(ADDON.getSetting('category'))

                self.onRedrawEPG(0, self.viewStartDate)
                if ADDON.getSetting('pokazpanel') == 'true':
                    self._showControl(self.C_MAIN_MOUSEPANEL_CONTROLS)
        else:
            self.close()

        if ADDON.getSetting('autostart_channel') == 'true':
            if ADDON.getSetting('autostart_channel_last') == 'true':
                try:
                    self.AutoPlayLastChannel()
                except ValueError:
                    self.AutoPlayByNumber()

            elif ADDON.getSetting('autostart_channel_number') != None:
                self.AutoPlayByNumber()

    def onSourceProgressUpdate(self, percentageComplete, additionalMessage = ""):
        if additionalMessage != "":
            self.setControlLabel(self.C_MAIN_LOADING_TIME_LEFT, additionalMessage)
            return not strings2.M_TVGUIDE_CLOSING and not self.isClosing

        deb('onSourceProgressUpdate')
        control = self.getControl(self.C_MAIN_LOADING_PROGRESS)
        if percentageComplete < 1:
            if control:
                control.setPercent(1)
            self.progressStartTime = datetime.datetime.now()
            self.progressPreviousPercentage = percentageComplete
        elif percentageComplete >= 100:
            if control:
                control.setPercent(100)
            self.progressStartTime = datetime.datetime.now()
            self.progressPreviousPercentage = 100
        elif percentageComplete != self.progressPreviousPercentage:
            if control:
                control.setPercent(percentageComplete)
            self.progressPreviousPercentage = percentageComplete
            delta = datetime.datetime.now() - self.progressStartTime

            if percentageComplete < 20:
                self.setControlLabel(self.C_MAIN_LOADING_TIME_LEFT, strings(CALCULATING_REMAINING_TIME))
            else:
                secondsLeft = int(delta.seconds) / float(percentageComplete) * (100.0 - percentageComplete)
                if secondsLeft > 30:
                    secondsLeft -= secondsLeft % 10

                self.setControlLabel(self.C_MAIN_LOADING_TIME_LEFT, strings(TIME_LEFT) % secondsLeft)

        return not strings2.M_TVGUIDE_CLOSING and not self.isClosing

    def onPlayBackStopped(self):
        deb('onPlayBackStopped')
        if not xbmc.Player().isPlaying() and not self.isClosing:
            self.viewStartDate = datetime.datetime.today()
            self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
            self.onRedrawEPG(self.channelIdx, self.viewStartDate, self._getCurrentProgramFocus)

    def _secondsToXposition(self, seconds):
        #deb('_secondsToXposition')
        return self.epgView.left + (seconds * self.epgView.width / 7200)

    def _findControlOnRight(self, point):
        #debug('_findControlOnRight')
        distanceToNearest = 10000
        nearestControl = None

        for elem in self.controlAndProgramList:
            control = elem.control
            (left, top) = control.getPosition()
            x = left + (control.getWidth() / 2)
            y = top + (control.getHeight() / 2)

            if point.x < x and point.y == y:
                distance = abs(point.x - x)
                if distance < distanceToNearest:
                    distanceToNearest = distance
                    nearestControl = control

        return nearestControl


    def _findControlOnLeft(self, point):
        #debug('_findControlOnLeft')
        distanceToNearest = 10000
        nearestControl = None

        for elem in self.controlAndProgramList:
            control = elem.control
            (left, top) = control.getPosition()
            x = left + (control.getWidth() / 2)
            y = top + (control.getHeight() / 2)

            if point.x > x and point.y == y:
                distance = abs(point.x - x)
                if distance < distanceToNearest:
                    distanceToNearest = distance
                    nearestControl = control

        return nearestControl

    def _findControlBelow(self, point):
        #debug('_findControlBelow')
        nearestControl = None

        for elem in self.controlAndProgramList:
            control = elem.control
            (leftEdge, top) = control.getPosition()
            y = top + (control.getHeight() / 2)

            if point.y < y:
                rightEdge = leftEdge + control.getWidth()
                if(leftEdge <= point.x < rightEdge
                   and (nearestControl is None or nearestControl.getPosition()[1] > top)):
                    nearestControl = control

        return nearestControl

    def _findControlAbove(self, point):
        #debug('_findControlAbove')
        nearestControl = None
        for elem in self.controlAndProgramList:
            control = elem.control
            (leftEdge, top) = control.getPosition()
            y = top + (control.getHeight() / 2)

            if point.y > y:
                rightEdge = leftEdge + control.getWidth()
                if(leftEdge <= point.x < rightEdge
                   and (nearestControl is None or nearestControl.getPosition()[1] < top)):
                    nearestControl = control

        return nearestControl

    def _findControlAt(self, point):
        debug('_findControlAt')
        for elem in self.controlAndProgramList:
            control = elem.control
            (left, top) = control.getPosition()
            bottom = top + control.getHeight()
            right = left + control.getWidth()

            if left <= point.x <= right and  top <= point.y <= bottom:
                return control

        return None

    def _getProgramFromControl(self, control):
        #deb('_getProgramFromControl')
        try:
            for elem in self.controlAndProgramList:
                if elem.control == control:
                    return elem.program
        except Exception, ex:
            deb('_getProgramFromControl Error: %s' % getExceptionString())
            raise
        return None

    def _getCurrentProgramFocus(self, point = None):
        try:
            if self.currentChannel:
                program = self.database.getCurrentProgram(self.currentChannel)
                if program is not None:
                    for elem in self.controlAndProgramList:
                        if elem.program.channel.id == program.channel.id and elem.program.startDate == program.startDate:
                            return elem.control
        except:
            pass
        return None

    def _hideControl(self, *controlIds):
        deb('_hideControl')
        """
        Visibility is inverted in skin
        """
        for controlId in controlIds:
            control = self.getControl(controlId)
            if control:
                control.setVisible(True)

    def _showControl(self, *controlIds):
        debug('_showControl')
        """
        Visibility is inverted in skin
        """
        for controlId in controlIds:
            control = self.getControl(controlId)
            if control:
                control.setVisible(False)

    def disableControl(self, controlId):
        #debug('disableControl %d' % controlId)
        control = self.getControl(controlId)
        if control:
            control.setVisible(False)
            control.setEnabled(False)

    def formatTime(self, timestamp):
        #debug('formatTime')
        format = xbmc.getRegion('time').replace(':%S', '').replace('%H%H', '%H')
        return timestamp.strftime(format)

    def formatDate(self, timestamp):
        debug('formatDate')
        format = xbmc.getRegion('dateshort')
        return timestamp.strftime(format)

    def setControlImage(self, controlId, image):
        debug('setControlImage')
        control = self.getControl(controlId)
        if control:
            control.setImage(image.encode('utf-8'))

    def setControlLabel(self, controlId, label):
        debug('setControlLabel')
        control = self.getControl(controlId)
        if control:
            control.setLabel(label)

    def setControlText(self, controlId, text):
        debug('setControlText')
        control = self.getControl(controlId)
        if control:
            control.setText(text)

    def updateTimebar(self, scheduleTimer = True):
        #debug('updateTimebar')
        if xbmc.Player().isPlaying():
            self.lastKeystroke = datetime.datetime.now()
        try:
            # move timebar to current time
            timeDelta = datetime.datetime.today() - self.viewStartDate
            control = self.getControl(self.C_MAIN_TIMEBAR)
            if control:
                (x, y) = control.getPosition()
                try:
                    # Sometimes raises:
                    # exceptions.RuntimeError: Unknown exception thrown from the call "setVisible"
                    control.setVisible(timeDelta.days == 0)
                except:
                    pass

                xPositionBar = self._secondsToXposition(timeDelta.seconds)
                control.setPosition(xPositionBar, y)
                if self.timebar:
                    self.timebar.setPosition(xPositionBar, y)

                if xPositionBar > (self.epgView.left + ((self.epgView.right - self.epgView.left) * 0.8)):
                    #Time bar exceeded EPG
                    #Check how long was since EPG was used
                    diff = datetime.datetime.now() - self.lastKeystroke
                    diffSeconds = (diff.days * 86400) + diff.seconds
                    debug('updateTimebar seconds since last user action %s' % diffSeconds)
                    if diffSeconds > 300:
                        deb('updateTimebar redrawing EPG start')
                        self.lastKeystroke = datetime.datetime.now()
                        self.viewStartDate = datetime.datetime.today()
                        self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30, seconds = self.viewStartDate.second)
                        self.onRedrawEPG(self.channelIdx, self.viewStartDate, self._getCurrentProgramFocus)
                        debug('updateTimebar redrawing EPG end')

            if scheduleTimer and not strings2.M_TVGUIDE_CLOSING and not self.isClosing:
                if self.updateTimebarTimer is not None:
                    self.updateTimebarTimer.cancel()
                self.updateTimebarTimer = threading.Timer(20, self.updateTimebar)
                self.updateTimebarTimer.start()
        except Exception:
            pass

    def refreshStreamsLoop(self):
        if self.autoUpdateCid == 'true':
            refreshTime = REFRESH_STREAMS_TIME
            if not strings2.M_TVGUIDE_CLOSING and not self.isClosing and self.database and self.recordService and self.playService and not self.recordService.isRecordOngoing() and not xbmc.Player().isPlaying() and not self.playService.isWorking() and self.checkUrl():
                if datetime.datetime.now().hour < 8:
                    refreshTime = 3600
                else:
                    diff = datetime.datetime.now() - self.lastKeystroke
                    diffSeconds = (diff.days * 86400) + diff.seconds
                    if diffSeconds > 60:
                        deb('refreshStreamsLoop refreshing all services')
                        self.database.reloadServices()
                        self.onRedrawEPG(self.channelIdx, self.viewStartDate, self._getCurrentProgramFocus)
                    else:
                        deb('refreshStreamsLoop services will be refreshed if no activity for 60s, currently no activity for %s seconds' % diffSeconds)
                        refreshTime = 60
            else:
                refreshTime = 600
                deb('refreshStreamsLoop delaying service refresh for %s seconds due to playback or record' % refreshTime)

            if not strings2.M_TVGUIDE_CLOSING and not self.isClosing:
                self.refreshStreamsTimer = threading.Timer(refreshTime, self.refreshStreamsLoop)
                self.refreshStreamsTimer.start()
        else:
            self.refreshStreamsTimer = None

    def checkUrl(slef, url = 'http://www.google.com'):
        try:
            import urllib2
            open = urllib2.urlopen(url, timeout = 3)
            if(open):
                open.read()
                return True
        except:
            pass
        return False

class PopupMenu(xbmcgui.WindowXMLDialog):
    C_POPUP_PLAY = 4000
    C_POPUP_CHOOSE_STREAM = 4001
    C_POPUP_REMIND = 4002 
    C_POPUP_CHANNELS = 4003
    C_POPUP_QUIT = 4004
    C_POPUP_RECORDINGS = 4006
    C_POPUP_RECORD = 4007
    C_POPUP_INFO = 4008
    C_POPUP_LISTS = 4009
    C_POPUP_NUMBER = 4010
    C_POPUP_EXTENDED = 4011
    C_POPUP_CHANNEL_LOGO = 4100
    C_POPUP_CHANNEL_TITLE = 4101
    C_POPUP_PROGRAM_TITLE = 4102
    C_POPUP_PROGRAM_TIME_RANGE = 4103
    C_POPUP_ADDON_SETTINGS = 4110
    C_POPUP_CATEGORY = 7004
    C_POPUP_FAQ = 4013

    LABEL_CHOOSE_STRM = CHOOSE_STRM_FILE

    def __new__(cls, database, program, showRemind):
        return super(PopupMenu, cls).__new__(cls, 'script-tvguide-menu.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, database, program, showRemind):
        """

        @type database: source.Database
        @param program:
        @type program: source.Program
        @param showRemind:
        """
        super(PopupMenu, self).__init__()
        self.database = database
        self.program = program
        self.showRemind = showRemind
        self.buttonClicked = None
        self.category = self.database.category
        self.categories = self.database.getAllCategories()


    def onInit(self):
        playControl = self.getControl(self.C_POPUP_PLAY)
        remindControl = self.getControl(self.C_POPUP_REMIND)
        channelLogoControl = self.getControl(self.C_POPUP_CHANNEL_LOGO)
        channelTitleControl = self.getControl(self.C_POPUP_CHANNEL_TITLE)
        programTitleControl = self.getControl(self.C_POPUP_PROGRAM_TITLE)
        chooseStrmControl = self.getControl(self.C_POPUP_CHOOSE_STREAM)
        programTimeRangeControl = self.getControl(self.C_POPUP_PROGRAM_TIME_RANGE)
        programRecordControl = self.getControl(self.C_POPUP_RECORD)

        try:
            listControl = self.getControl(self.C_POPUP_CATEGORY)

            items = list()
            categories = PREDEFINED_CATEGORIES + sorted(list(self.categories), key=lambda x: x.lower())
            for label in categories:
                item = xbmcgui.ListItem(label)
                items.append(item)

            listControl.addItems(items)
            if self.category and self.category in categories:
                index = categories.index(self.category)
                if index >= 0:
                    listControl.selectItem(index)
        except:
            deb('Categories not supported by current skin')
            self.category = None

        playControl.setLabel(strings(WATCH_CHANNEL, self.program.channel.title))
        if not self.program.channel.isPlayable():
            playControl.setEnabled(False)
            self.setFocusId(self.C_POPUP_NUMBER)

        self.LABEL_CHOOSE_STRM = getStateLabel(chooseStrmControl, 0, CHOOSE_STRM_FILE)
        LABEL_REMOVE_STRM = getStateLabel(chooseStrmControl, 1, REMOVE_STRM_FILE)
        LABEL_REMIND      = getStateLabel(remindControl,     0, REMIND_PROGRAM)
        LABEL_DONT_REMIND = getStateLabel(remindControl,     1, DONT_REMIND_PROGRAM)

        if self.database.getCustomStreamUrl(self.program.channel):
            chooseStrmControl.setLabel(strings(LABEL_REMOVE_STRM))
        else:
            chooseStrmControl.setLabel(strings(self.LABEL_CHOOSE_STRM))

        if self.program.channel.logo is not None:
            channelLogoControl.setImage(self.program.channel.logo)
            channelTitleControl.setVisible(False)
        else:
            channelTitleControl.setLabel(self.program.channel.title)
            channelLogoControl.setVisible(False)

        programTitleControl.setLabel(self.program.title)

        if self.showRemind:
            remindControl.setLabel(strings(LABEL_REMIND))
        else:
            remindControl.setLabel(strings(LABEL_DONT_REMIND))

        if self.program.recordingScheduled:
            programRecordControl.setLabel(strings(RECORD_PROGRAM_CANCEL_STRING))
        else:
            programRecordControl.setLabel(strings(RECORD_PROGRAM_STRING))

        if programTimeRangeControl is not None:
            programTimeRangeControl.setLabel('%s - %s' % (self.formatTime(self.program.startDate), self.formatTime(self.program.endDate)))

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK]:
            self.close()
            return

        elif action.getId() in [KEY_CONTEXT_MENU] and xbmc.getCondVisibility('!Control.HasFocus(7004)'):
            self.close()
            return

        elif action.getId() in [KEY_CONTEXT_MENU] and xbmc.getCondVisibility('Control.HasFocus(7004)'):
            cList = self.getControl(self.C_POPUP_CATEGORY)
            if cList.getSelectedPosition() < len(PREDEFINED_CATEGORIES):
                return

            item = cList.getSelectedItem()
            if item:
                self.category = item.getLabel()

            dialog = xbmcgui.Dialog()
            ret = dialog.select("%s" % self.category, [strings(30985).encode('utf-8', 'replace'), strings(30986).encode('utf-8', 'replace'), strings(30987).encode('utf-8', 'replace')])
            if ret < 0:
                return

            categories = {}
            categories[self.category] = []
            for name, cat in self.database.getCategoryMap():
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(name)

            if ret == 0:
                channelList = sorted([channel.title for channel in self.database.getChannelList(onlyVisible=True, customCategory=self.category, excludeCurrentCategory=True)])
                string = strings(30989).encode('utf-8', 'replace') % self.category
                ret = dialog.multiselect(string, channelList)
                if ret is None:
                    return
                if not ret:
                    ret = []
                channels = []
                for i in ret:
                    channels.append(channelList[i])

                for channel in channels:
                    if channel not in categories[self.category]:
                        categories[self.category].append(channel)

            elif ret == 1:
                channelList = sorted([channel.title for channel in self.database.getChannelList(onlyVisible=True, customCategory=self.category)])
                string = strings(30990).encode('utf-8', 'replace') % self.category
                ret = dialog.multiselect(string, channelList)
                if ret is None:
                    return
                if not ret:
                    ret = []
                channels = []
                for i in ret:
                    channelList[i] = ""
                categories[self.category] = []
                for name in channelList:
                    if name:
                        categories[self.category].append(name)

            elif ret == 2:
                categories[self.category] = []

            self.database.saveCategoryMap(categories)
            self.categories = [category for category in categories if category]
            self.buttonClicked = self.C_POPUP_CATEGORY


    def onClick(self, controlId):
        if controlId == self.C_POPUP_CHOOSE_STREAM and self.database.getCustomStreamUrl(self.program.channel):
            self.database.deleteCustomStreamUrl(self.program.channel)
            chooseStrmControl = self.getControl(self.C_POPUP_CHOOSE_STREAM)
            chooseStrmControl.setLabel(strings(self.LABEL_CHOOSE_STRM))

            if not self.program.channel.isPlayable():
                playControl = self.getControl(self.C_POPUP_PLAY)
                playControl.setEnabled(False)

        elif controlId == self.C_POPUP_CATEGORY:
            cList = self.getControl(self.C_POPUP_CATEGORY)
            if cList.getSelectedPosition() == 0:
                self.category = None
            else:
                item = cList.getSelectedItem()
                if item:
                    self.category = item.getLabel()
            self.buttonClicked = controlId
            self.close()
        elif controlId == 4012:
            dialog = xbmcgui.Dialog()
            cat = dialog.input(strings(30984).encode('utf-8', 'replace'), type=xbmcgui.INPUT_ALPHANUM)
            if cat:
                categories = set(self.categories)
                categories.add(cat)
                self.categories = list(set(categories))
                items = list()
                categories = PREDEFINED_CATEGORIES + sorted(list(self.categories), key=lambda x: x.lower())
                for label in categories:
                    item = xbmcgui.ListItem(label)
                    items.append(item)
                listControl = self.getControl(self.C_POPUP_CATEGORY)
                listControl.reset()
                listControl.addItems(items)
                listControl.selectItem(categories.index(cat))
        else:
            self.buttonClicked = controlId
            self.close()

    def onFocus(self, controlId):
        pass

    def formatTime(self, timestamp):
        deb('formatTime')
        format = xbmc.getRegion('time').replace(':%S', '').replace('%H%H', '%H')
        return timestamp.strftime(format)

    def getControl(self, controlId):
        try:
            return super(PopupMenu, self).getControl(controlId)
        except:
            pass
        return None

class ChannelsMenu(xbmcgui.WindowXMLDialog):
    C_CHANNELS_LIST = 6000
    C_CHANNELS_SELECTION_VISIBLE = 6001
    C_CHANNELS_SELECTION = 6002
    C_CHANNELS_SAVE = 6003
    C_CHANNELS_CANCEL = 6004

    def __new__(cls, database, channel=None):
        return super(ChannelsMenu, cls).__new__(cls, 'script-tvguide-channels.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, database, channel=None):
        """

        @type database: source.Database
        """
        super(ChannelsMenu, self).__init__()
        self.database = database
        self.channelList = database.getChannelList(onlyVisible = False)
        self.swapInProgress = False
        try:
            self.startChannelIndex = self.channelList.index(channel)
        except:
            self.startChannelIndex = -1

    def onInit(self):
        self.updateChannelList()
        self.setFocusId(self.C_CHANNELS_LIST)

        if self.startChannelIndex > -1:
            try:
                listControl = self.getControl(self.C_CHANNELS_LIST)
                listControl.selectItem(self.startChannelIndex)
            except:
                pass
            self.startChannelIndex = -1

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK, KEY_CONTEXT_MENU] or action.getButtonCode() in [KEY_CONTEXT]:
            self.close()
            return

        if self.getFocusId() == self.C_CHANNELS_LIST and action.getId() == ACTION_LEFT:
            listControl = self.getControl(self.C_CHANNELS_LIST)
            idx = listControl.getSelectedPosition()
            buttonControl = self.getControl(self.C_CHANNELS_SELECTION)
            buttonControl.setLabel('%s' % self.channelList[idx].title)

            self.getControl(self.C_CHANNELS_SELECTION_VISIBLE).setVisible(False)
            self.setFocusId(self.C_CHANNELS_SELECTION)

        elif self.getFocusId() == self.C_CHANNELS_SELECTION and action.getId() in [ACTION_RIGHT, ACTION_SELECT_ITEM]:
            self.getControl(self.C_CHANNELS_SELECTION_VISIBLE).setVisible(True)
            xbmc.sleep(350)
            self.setFocusId(self.C_CHANNELS_LIST)

        elif self.getFocusId() == self.C_CHANNELS_SELECTION and action.getId() == ACTION_UP:
            listControl = self.getControl(self.C_CHANNELS_LIST)
            idx = listControl.getSelectedPosition()
            if idx > 0:
                self.swapChannels(idx, idx - 1)

        elif self.getFocusId() == self.C_CHANNELS_SELECTION and action.getId() == ACTION_DOWN:
            listControl = self.getControl(self.C_CHANNELS_LIST)
            idx = listControl.getSelectedPosition()
            if idx < listControl.size() - 1:
                self.swapChannels(idx, idx + 1)


    def onClick(self, controlId):
        if controlId == self.C_CHANNELS_LIST:
            listControl = self.getControl(self.C_CHANNELS_LIST)
            item = listControl.getSelectedItem()
            channel = self.channelList[int(item.getProperty('idx'))]
            channel.visible = not channel.visible

            if channel.visible:
                iconImage = 'tvguide-channel-visible.png'
            else:
                iconImage = 'tvguide-channel-hidden.png'
            item.setIconImage(iconImage)

        elif controlId == self.C_CHANNELS_SAVE:
            self.database.saveChannelList(self.close, self.channelList)

        elif controlId == self.C_CHANNELS_CANCEL:
            self.close()


    def onFocus(self, controlId):
        pass

    def updateChannelList(self):
        listControl = self.getControl(self.C_CHANNELS_LIST)
        listControl.reset()
        for idx, channel in enumerate(self.channelList):
            if channel.visible:
                iconImage = 'tvguide-channel-visible.png'
            else:
                iconImage = 'tvguide-channel-hidden.png'

            items = xbmcgui.ListItem('%3d. %s' % (idx+1, channel.title), iconImage = iconImage)
            items.setProperty('idx', str(idx))
            listControl.addItem(items)

    def updateListItem(self, idx, item):
        channel = self.channelList[idx]
        item.setLabel('%3d. %s' % (idx+1, channel.title))

        if channel.visible:
            iconImage = 'tvguide-channel-visible.png'
        else:
            iconImage = 'tvguide-channel-hidden.png'
        item.setIconImage(iconImage)
        item.setProperty('idx', str(idx))

    def swapChannels(self, fromIdx, toIdx):
        if self.swapInProgress:
            return
        self.swapInProgress = True

        c = self.channelList[fromIdx]
        self.channelList[fromIdx] = self.channelList[toIdx]
        self.channelList[toIdx] = c

        # recalculate weight
        for idx, channel in enumerate(self.channelList):
            channel.weight = idx

        listControl = self.getControl(self.C_CHANNELS_LIST)
        self.updateListItem(fromIdx, listControl.getListItem(fromIdx))
        self.updateListItem(toIdx, listControl.getListItem(toIdx))

        listControl.selectItem(toIdx)
        xbmc.sleep(50)
        self.swapInProgress = False



class StreamSetupDialog(xbmcgui.WindowXMLDialog):
    C_STREAM_STRM_TAB = 101
    C_STREAM_FAVOURITES_TAB = 102
    C_STREAM_ADDONS_TAB = 103
    C_STREAM_STRM_BROWSE = 1001
    C_STREAM_STRM_FILE_LABEL = 1005
    C_STREAM_STRM_PREVIEW = 1002
    C_STREAM_STRM_OK = 1003
    C_STREAM_STRM_CANCEL = 1004
    C_STREAM_FAVOURITES = 2001
    C_STREAM_FAVOURITES_PREVIEW = 2002
    C_STREAM_FAVOURITES_OK = 2003
    C_STREAM_FAVOURITES_CANCEL = 2004
    C_STREAM_ADDONS = 3001
    C_STREAM_ADDONS_STREAMS = 3002
    C_STREAM_ADDONS_NAME = 3003
    C_STREAM_ADDONS_DESCRIPTION = 3004
    C_STREAM_ADDONS_PREVIEW = 3005
    C_STREAM_ADDONS_OK = 3006
    C_STREAM_ADDONS_CANCEL = 3007

    C_STREAM_VISIBILITY_MARKER = 100

    VISIBLE_STRM = 'strm'
    VISIBLE_FAVOURITES = 'favourites'
    VISIBLE_ADDONS = 'addons'

    def __new__(cls, database, channel):
        return super(StreamSetupDialog, cls).__new__(cls, 'script-tvguide-streamsetup.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, database, channel):
        """
        @type database: source.Database
        @type channel:source.Channel
        """
        super(StreamSetupDialog, self).__init__()
        self.database = database
        self.channel = channel
        self.previousAddonId = None
        self.strmFile = None
        self.streamingService = streaming.StreamsService()

    def close(self):
        if xbmc.Player().isPlaying():
            xbmc.Player().stop()
        super(StreamSetupDialog, self).close()


    def onInit(self):
        self.getControl(self.C_STREAM_VISIBILITY_MARKER).setLabel(self.VISIBLE_STRM)

        favourites = self.streamingService.loadFavourites()
        items = list()
        for label, value in favourites:
            item = xbmcgui.ListItem(label)
            item.setProperty('stream', value)
            items.append(item)

        listControl = self.getControl(StreamSetupDialog.C_STREAM_FAVOURITES)
        listControl.addItems(items)

        items = list()
        for id in self.streamingService.getAddons():
            try:
                addon = xbmcaddon.Addon(id) # raises Exception if addon is not installed
                item = xbmcgui.ListItem(addon.getAddonInfo('name'), iconImage=addon.getAddonInfo('icon'))
                item.setProperty('addon_id', id)
                items.append(item)
            except Exception:
                pass
        listControl = self.getControl(StreamSetupDialog.C_STREAM_ADDONS)
        listControl.addItems(items)
        self.updateAddonInfo()



    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK, KEY_CONTEXT_MENU] or action.getButtonCode() in [KEY_CONTEXT]:
            self.close()
            return

        elif self.getFocusId() == self.C_STREAM_ADDONS:
            self.updateAddonInfo()



    def onClick(self, controlId):
        if controlId == self.C_STREAM_STRM_BROWSE:
            stream = xbmcgui.Dialog().browse(1, ADDON.getLocalizedString(30304), 'video', '.strm')
            if stream:
                self.database.setCustomStreamUrl(self.channel, stream)
                self.getControl(self.C_STREAM_STRM_FILE_LABEL).setText(stream)
                self.strmFile = stream

        elif controlId == self.C_STREAM_ADDONS_OK:
            listControl = self.getControl(self.C_STREAM_ADDONS_STREAMS)
            item = listControl.getSelectedItem()
            if item:
                stream = item.getProperty('stream')
                self.database.setCustomStreamUrl(self.channel, stream)
            self.close()

        elif controlId == self.C_STREAM_FAVOURITES_OK:
            listControl = self.getControl(self.C_STREAM_FAVOURITES)
            item = listControl.getSelectedItem()
            if item:
                stream = item.getProperty('stream')
                self.database.setCustomStreamUrl(self.channel, stream)
            self.close()

        elif controlId == self.C_STREAM_STRM_OK:
            self.database.setCustomStreamUrl(self.channel, self.strmFile)
            self.close()

        elif controlId in [self.C_STREAM_ADDONS_CANCEL, self.C_STREAM_FAVOURITES_CANCEL, self.C_STREAM_STRM_CANCEL]:
            self.close()

        elif controlId in [self.C_STREAM_ADDONS_PREVIEW, self.C_STREAM_FAVOURITES_PREVIEW, self.C_STREAM_STRM_PREVIEW]:
            if xbmc.Player().isPlaying():
                xbmc.Player().stop()
                self.getControl(self.C_STREAM_ADDONS_PREVIEW).setLabel(strings(PREVIEW_STREAM))
                self.getControl(self.C_STREAM_FAVOURITES_PREVIEW).setLabel(strings(PREVIEW_STREAM))
                self.getControl(self.C_STREAM_STRM_PREVIEW).setLabel(strings(PREVIEW_STREAM))
                return

            stream = None
            visible = self.getControl(self.C_STREAM_VISIBILITY_MARKER).getLabel()
            if visible == self.VISIBLE_ADDONS:
                listControl = self.getControl(self.C_STREAM_ADDONS_STREAMS)
                item = listControl.getSelectedItem()
                if item:
                    stream = item.getProperty('stream')
            elif visible == self.VISIBLE_FAVOURITES:
                listControl = self.getControl(self.C_STREAM_FAVOURITES)
                item = listControl.getSelectedItem()
                if item:
                    stream = item.getProperty('stream')
            elif visible == self.VISIBLE_STRM:
                stream = self.strmFile

            if stream is not None:
                xbmc.Player().play(item = stream, windowed = True)
                if xbmc.Player().isPlaying():
                    self.getControl(self.C_STREAM_ADDONS_PREVIEW).setLabel(strings(STOP_PREVIEW))
                    self.getControl(self.C_STREAM_FAVOURITES_PREVIEW).setLabel(strings(STOP_PREVIEW))
                    self.getControl(self.C_STREAM_STRM_PREVIEW).setLabel(strings(STOP_PREVIEW))


    def onFocus(self, controlId):
        if controlId == self.C_STREAM_STRM_TAB:
            self.getControl(self.C_STREAM_VISIBILITY_MARKER).setLabel(self.VISIBLE_STRM)
        elif controlId == self.C_STREAM_FAVOURITES_TAB:
            self.getControl(self.C_STREAM_VISIBILITY_MARKER).setLabel(self.VISIBLE_FAVOURITES)
        elif controlId == self.C_STREAM_ADDONS_TAB:
            self.getControl(self.C_STREAM_VISIBILITY_MARKER).setLabel(self.VISIBLE_ADDONS)


    def updateAddonInfo(self):
        listControl = self.getControl(self.C_STREAM_ADDONS)
        item = listControl.getSelectedItem()
        if item is None:
            return

        if item.getProperty('addon_id') == self.previousAddonId:
            return

        self.previousAddonId = item.getProperty('addon_id')
        addon = xbmcaddon.Addon(id = item.getProperty('addon_id'))
        self.getControl(self.C_STREAM_ADDONS_NAME).setLabel('%s' % addon.getAddonInfo('name'))
        self.getControl(self.C_STREAM_ADDONS_DESCRIPTION).setText(addon.getAddonInfo('description'))

        streams = self.streamingService.getAddonStreams(item.getProperty('addon_id'))
        items = list()
        for (label, stream) in streams:
            item = xbmcgui.ListItem(label)
            item.setProperty('stream', stream)
            items.append(item)
        listControl = self.getControl(StreamSetupDialog.C_STREAM_ADDONS_STREAMS)
        listControl.reset()
        listControl.addItems(items)

class ChooseStreamAddonDialog(xbmcgui.WindowXMLDialog):
    C_SELECTION_LIST = 1000

    def __new__(cls, addons):
        return super(ChooseStreamAddonDialog, cls).__new__(cls, 'script-tvguide-streamaddon.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, addons):
        super(ChooseStreamAddonDialog, self).__init__()
        self.addons = addons
        self.stream = None

    def onInit(self):
        items = list()
        for id, label, url in self.addons:
            addon = xbmcaddon.Addon(id)

            item = xbmcgui.ListItem(label, addon.getAddonInfo('name'), addon.getAddonInfo('icon'))
            item.setProperty('stream', url)
            items.append(item)

        listControl = self.getControl(ChooseStreamAddonDialog.C_SELECTION_LIST)
        listControl.addItems(items)

        self.setFocus(listControl)

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK]:
            self.close()


    def onClick(self, controlId):
        if controlId == ChooseStreamAddonDialog.C_SELECTION_LIST:
            listControl = self.getControl(ChooseStreamAddonDialog.C_SELECTION_LIST)
            self.stream = listControl.getSelectedItem().getProperty('stream')
            self.close()

    def onFocus(self, controlId):
        pass

class InfoDialog(xbmcgui.WindowXMLDialog):
    def __new__(cls, program):
        return super(InfoDialog, cls).__new__(cls, 'DialogInfo.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, program):
        super(InfoDialog, self).__init__()
        self.program = program

    def setControlLabel(self, controlId, label):
        control = self.getControl(controlId)
        if control:
            control.setLabel(label)

    def formatTime(self, timestamp):
        format = xbmc.getRegion('time').replace(':%S', '').replace('%H%H', '%H')
        return timestamp.strftime(format)

    def setControlText(self, controlId, text):
        control = self.getControl(controlId)
        if control:
            control.setText(text)

    def setControlImage(self, controlId, image):
        control = self.getControl(controlId)
        if control:
            control.setImage(image)

    def onInit(self):
        if self.program is None:
            return

        self.setControlLabel(C_MAIN_TITLE, '%s' % self.program.title)
        self.setControlLabel(C_MAIN_TIME, '%s - %s' % (self.formatTime(self.program.startDate), self.formatTime(self.program.endDate)))
        if self.program.description:
            description = self.program.description
        else:
            description = strings("")


        if skin_separate_category or skin_separate_year_of_production or skin_separate_director or skin_separate_episode or skin_separate_allowed_age_icon or skin_separate_program_progress or skin_separate_program_actors:
            #This mean we'll need to parse program description
            descriptionParser = src.ProgramDescriptionParser(description)
            if skin_separate_category:
                try:
                    categoryControl = self.getControl(C_PROGRAM_CATEGORY)
                    category = descriptionParser.extractCategory()
                    categoryControl.setText(category)
                except:
                    pass
            if skin_separate_year_of_production:
                try:
                    productionDateControl = self.getControl(C_PROGRAM_PRODUCTION_DATE)
                    year = descriptionParser.extractProductionDate()
                    productionDateControl.setText(year)
                except:
                    pass
            if skin_separate_director:
                try:
                    directorControl = self.getControl(C_PROGRAM_DIRECTOR)
                    director = descriptionParser.extractDirector()
                    directorControl.setText(director)
                except:
                    pass
            if skin_separate_episode:
                try:
                    episodeControl = self.getControl(C_PROGRAM_EPISODE)
                    episode = descriptionParser.extractEpisode()
                    episodeControl.setText(episode)
                except:
                    pass
            if skin_separate_allowed_age_icon:
                try:
                    ageImageControl = self.getControl(C_PROGRAM_AGE_ICON)
                    icon = descriptionParser.extractAllowedAge()
                    ageImageControl.setImage(icon)
                except:
                    pass
            if skin_separate_program_actors:
                try:
                    actorsControl = self.getControl(C_PROGRAM_ACTORS)
                    actors = descriptionParser.extractActors()
                    actorsControl.setText(actors)
                except:
                    pass

            description = descriptionParser.description

        self.setControlText(C_MAIN_DESCRIPTION, description)

        if self.program.channel.logo is not None:
            self.setControlImage(C_MAIN_LOGO, self.program.channel.logo)
        if self.program.imageSmall is not None:
            self.setControlImage(C_MAIN_IMAGE, self.program.imageSmall)
        if self.program.imageSmall is None:
            self.setControlImage(C_MAIN_IMAGE, 'tvguide-logo-epg.png')
        if self.program.imageLarge == 'live':
            self.setControlImage(C_MAIN_LIVE, 'live.png')
        else:
            self.setControlImage(C_MAIN_LIVE, '')

        self.stdat = time.mktime(self.program.startDate.timetuple())
        self.endat = time.mktime(self.program.endDate.timetuple())
        self.nodat = time.mktime(datetime.datetime.now().timetuple())
        self.per =  100 -  ((self.endat - self.nodat)/ ((self.endat - self.stdat)/100))
        if self.per > 0 and self.per < 100:
            self.getControl(C_PROGRAM_PROGRESS).setVisible(True)
            self.getControl(C_PROGRAM_PROGRESS).setPercent(self.per)
        else:
            self.getControl(C_PROGRAM_PROGRESS).setVisible(False)

        if self.per > 0 and self.per < 100:
            self.getControl(C_PROGRAM_SLIDER).setVisible(True)
            self.getControl(C_PROGRAM_SLIDER).setPercent(self.per)
        else:
            self.getControl(C_PROGRAM_SLIDER).setVisible(False)

    def setChannel(self, channel):
        self.channel = channel

    def getChannel(self):
        return self.channel

    def onAction(self, action):
        if action.getId() in [ACTION_SHOW_INFO, ACTION_PREVIOUS_MENU, KEY_NAV_BACK, ACTION_PARENT_DIR] or (action.getButtonCode() == KEY_INFO and KEY_INFO != 0) or (action.getButtonCode() == KEY_STOP and KEY_STOP != 0):
            self.close()

    def onClick(self, controlId):
        if controlId == 1000:
            self.close()

class Pla(xbmcgui.WindowXMLDialog):
    def __new__(cls, program, database, urlList, epg):
        return super(Pla, cls).__new__(cls, 'Vid.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, program, database, urlList, epg):
        #debug('Pla __init__')
        super(Pla, self).__init__()
        self.epg = epg
        self.database = database
        self.controlAndProgramList = list()
        self.ChannelChanged = 0
        self.mouseCount = 0
        self.isClosing = False
        self.playbackStarted = False
        self.key_right_left_show_next = ADDON.getSetting('key_right_left_show_next')
        self.playButtonAsSchedule = False
        self.videoOSD = None
        self.displayService = True
        self.displayServiceTimer = None
        self.showOsdOnPlay = False
        self.displayAutoOsd = False
        self.ignoreInput = False
        self.ctrlService = None
        self.timer = None
        self.channel_number_input = False
        if ADDON.getSetting('show_osd_on_play') == 'true':
            self.showOsdOnPlay = True
            self.displayAutoOsd = True
        if program is not None:
            if urlList is None:
                urlList = database.getStreamUrlList(program.channel)
            self.program = program
        elif self.epg.currentChannel:
            self.program = self.getCurrentProgram()
        else:
            deb('Pla currentChannel is none! Closing Pla!')
            self.isClosing = True
            return

        if urlList is not None:
            self.play(urlList)

        threading.Timer(0, self.waitForPlayBackStopped).start()

    def onInit(self):
        if self.isClosing:
            self.closeOSD()
            return
        if not self.ctrlService:
            self.ctrlService = self.getControl(C_VOSD_SERVICE)

        if ADDON.getSetting('info.osd') == "true":
            self.epg.setControlLabel(C_MAIN_CHAN_PLAY, '%s' % (self.program.channel.title))
            self.epg.setControlLabel(C_MAIN_PROG_PLAY, '%s' % (self.program.title))
            self.epg.setControlLabel(C_MAIN_TIME_PLAY, '%s - %s' % (self.epg.formatTime(self.program.startDate), self.epg.formatTime(self.program.endDate)))
            self.epg.setControlLabel(C_MAIN_NUMB_PLAY, '%s' % (self.database.getCurrentChannelIdx(self.program.channel) + 1))

    def play(self, urlList):
        self.epg.playService.playUrlList(urlList, resetReconnectCounter=True)

    def playShortcut(self):
        self.channel_number_input = False
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes=self.viewStartDate.minute % 30,
                                                 seconds=self.viewStartDate.second)
        channelList = self.database.getChannelList(onlyVisible=True)
        if ADDON.getSetting('channel.shortcut') == 'false':
            for i in range(len(channelList)):
                if self.channel_number == channelList[i].id:
                     self.channelIdx = i
                     break
        else:
            self.channelIdx = (int(self.channel_number) -1)
            self.channel_number = ""
            self.getControl(9999).setLabel(self.channel_number)

        channel = Channel(id='', title='', logo='', streamUrl='', visible='', weight='')
        program = Program(channel=channelList[self.channelIdx], title='', startDate='', endDate='', description='', imageLarge='', imageSmall='', categoryA='',categoryB='')
        self.playChannel(program.channel)

    def onAction(self, action):
        debug('Pla onAction keyId %d, buttonCode %d' % (action.getId(), action.getButtonCode()))

        if action.getId() == ACTION_PREVIOUS_MENU or action.getId() == ACTION_STOP or (action.getButtonCode() == KEY_STOP and KEY_STOP != 0) or (action.getId() == KEY_STOP and KEY_STOP != 0):
            self.epg.playService.stopPlayback()
            self.closeOSD()

        elif action.getId() == KEY_NAV_BACK:
            self.closeOSD()
            if ADDON.getSetting('navi_back_stop_play') == 'true' or ADDON.getSetting('start_video_minimalized') == 'false':
                self.epg.playService.stopPlayback()
            else:
                #xbmc.executebuiltin("Action(FullScreen)")
                #if ADDON.getSetting('start_video_minimalized') == 'false':
                    #xbmc.executebuiltin("Action(FullScreen)")
                    #xbmc.executebuiltin("Action(Back)")
                    #xbmc.sleep(300)
                self.epg._showEPG()
                
                #if ADDON.getSetting('start_video_minimalized') == 'false':
                    #xbmc.executebuiltin("Action(FullScreen)")
                    #xbmc.executebuiltin("Action(Back)")
                    #self.epg.redrawagain = True
                    #self.epg._showEPG()
                    #pass
            return

        elif self.ignoreInput:
            debug('Pla ignoring key')
            return

        if action.getId() == KEY_CODEC_INFO: #przysik O
            xbmc.executebuiltin("Action(CodecInfo)")

        elif action.getId() == ACTION_PAGE_UP or (action.getButtonCode() == KEY_PP and KEY_PP != 0) or (action.getId() == KEY_PP and KEY_PP != 0):
            self.ignoreInput = True
            self.ChannelChanged = 1
            self._channelUp()
            self.ignoreInput = False
            return

        elif action.getId() == ACTION_PAGE_DOWN or (action.getButtonCode() == KEY_PM and KEY_PM != 0) or (action.getId() == KEY_PM and KEY_PM != 0):
            self.ignoreInput = True
            self.ChannelChanged = 1
            self._channelDown()
            self.ignoreInput = False
            return

        elif action.getId() == KEY_CONTEXT_MENU or action.getButtonCode() == KEY_CONTEXT:
            self.ignoreInput = True
            self.changeStream()
            self.ignoreInput = False
            return

        elif self.playbackStarted == False:
            debug('Playback has not started yet, canceling all key requests')
            return

        elif action.getId() == ACTION_SHOW_INFO or (action.getButtonCode() == KEY_INFO and KEY_INFO != 0) or (action.getId() == KEY_INFO and KEY_INFO != 0):
            try:
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:
                    self.program = self.getCurrentProgram()
                    self.epg.Info(self.program)
                elif list == 1:
                    self.program = self.getCurrentProgram()
                    self.epg.ExtendedInfo(self.program)
            except:
                pass
            return

        elif action.getButtonCode() == KEY_VOL_DOWN or (action.getId() == ACTION_LEFT and self.key_right_left_show_next == 'false'):
            xbmc.executebuiltin("Action(VolumeDown)")

        elif action.getButtonCode() == KEY_VOL_UP or (action.getId() == ACTION_RIGHT and self.key_right_left_show_next == 'false'):
            xbmc.executebuiltin("Action(VolumeUp)")

        elif (action.getId() == ACTION_LEFT and self.key_right_left_show_next == 'true'):
            self.showVidOsd(ACTION_LEFT)

        elif (action.getId() == ACTION_RIGHT and self.key_right_left_show_next == 'true'):
            self.showVidOsd(ACTION_RIGHT)

        elif (action.getId() == ACTION_UP):
            self.showVidOsd(ACTION_UP)

        elif (action.getId() == ACTION_DOWN):
            self.showVidOsd(ACTION_DOWN)

        elif (action.getId() == ACTION_SELECT_ITEM):
            try:
                if ADDON.getSetting('VidOSD_on_select') == 'true':
                    self.showVidOsd()
                else:
                    self.program = self.getCurrentProgram()
                    self.epg.Info(self.program)
            except:
                pass
            return

        elif (action.getButtonCode() == KEY_HOME2 and KEY_HOME2 != 0) or (action.getId() == KEY_HOME2 and KEY_HOME2 != 0):
            xbmc.executebuiltin("SendClick(VideoLibrary)")

        elif action.getId() == ACTION_MOUSE_MOVE and xbmc.Player().isPlaying():
            self.mouseCount = self.mouseCount + 1
            if self.mouseCount > 15:
                self.mouseCount = 0
                osd = VideoOSD(self)
                osd.doModal()
                del osd

        elif action.getButtonCode() == KEY_SWITCH_TO_LAST:
            deb('Pla play last channel')
            channel = self.epg.getLastChannel()
            if channel:
                self.playChannel(channel)

        if (ADDON.getSetting('channel.shortcut') != 'false'):
            digit = None
            if not self.channel_number_input:
                code = action.getButtonCode() - 61488
                action_code = action.getId() - 58
                action_code_2 = action.getId() - 140
                if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                    digit = None
                    if (code >= 0 and code <= 9):
                        digit = code
                    elif (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = action_code_2
                    else:
                        digit = action_code
                    self.channel_number_input = True
                    self.channel_number = str(digit)
                    self.getControl(9999).setLabel(self.channel_number)
                    if self.timer and self.timer.is_alive():
                        self.timer.cancel()
                    self.timer = threading.Timer(2, self.playShortcut)
                    self.timer.start()


            if self.channel_number_input:
                if digit == None:
                    code = action.getButtonCode() - 61488
                    action_code = action.getId() - 58
                    action_code_2 = action.getId() - 140
                    if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = None
                        if (code >= 0 and code <= 9):
                            digit = code
                        elif (action_code_2 >= 0 and action_code_2 <= 9):
                            digit = action_code_2
                        else:
                            digit = action_code
                    if digit != None:
                        self.channel_number = "%s%d" % (self.channel_number.strip('_'),digit)
                        self.getControl(9999).setLabel(self.channel_number)
                        if self.timer and self.timer.is_alive():
                            self.timer.cancel()
                        self.timer = threading.Timer(2, self.playShortcut)
                        self.timer.start()

        if (ADDON.getSetting('channel.shortcut') == 'false'):
            digit = None
            if not self.channel_number_input:
                code = action.getButtonCode() - 61488
                action_code = action.getId() - 58
                action_code_2 = action.getId() - 140
                if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                    digit = None
                    if (code >= 0 and code <= 9):
                        digit = code
                    elif (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = action_code_2
                    else:
                        digit = action_code
                    xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
                    return

            if self.channel_number_input:
                if digit == None:
                    code = action.getButtonCode() - 61488
                    action_code = action.getId() - 58
                    action_code_2 = action.getId() - 140
                    if (code >= 0 and code <= 9) or (action_code >= 0 and action_code <= 9) or (action_code_2 >= 0 and action_code_2 <= 9):
                        digit = None
                        if (code >= 0 and code <= 9):
                            digit = code
                        elif (action_code_2 >= 0 and action_code_2 <= 9):
                            digit = action_code_2
                        else:
                            digit = action_code
                    if digit != None:
                        xbmcgui.Dialog().notification(strings(30353).encode('utf-8'), strings(30354).encode('utf-8'))
                        return

    def onAction2(self, action, program = None):
        debug('Pla onAction2')
        if action in [ACTION_STOP, KEY_NAV_BACK]:
            self.epg.playService.stopPlayback()
            self.closeOSD()

        elif action == ACTION_SHOW_INFO:
            try:
                if program is None:
                    program = self.getCurrentProgram()
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:  
                    self.epg.Info(program)
                elif list == 1:
                    self.epg.ExtendedInfo(program)
            except:
                pass
            return

        elif action == ACTION_PAGE_UP:
            self.ChannelChanged = 1
            self._channelUp()

        elif action == ACTION_PAGE_DOWN:
            self.ChannelChanged = 1
            self._channelDown()

    def onPlayBackStopped(self):
        debug('Pla onPlayBackStopped')
        self.closeOSD()

    def waitForPlayBackStopped(self):
        self.wait = True

        xbmc.sleep(50)
        while self.epg.playService.isWorking() == True and not self.isClosing:
            xbmc.sleep(100)

        while self.wait == True and not self.isClosing:
            if xbmc.Player().isPlaying() and not strings2.M_TVGUIDE_CLOSING and not self.isClosing and not self.epg.playService.isWorking():
                self.playbackStarted = True
                if self.displayService:
                    self.displayServiceOnOSD()
                if self.displayAutoOsd and self.showOsdOnPlay:
                    self.displayAutoOsd = False
                    self.showVidOsd(AUTO_OSD)
                else:
                    xbmc.sleep(200)
            else:
                xbmc.sleep(100)
                self.playbackStarted = False
                if not self.isClosing and (self.ChannelChanged == 1 or self.epg.playService.isWorking() == True):
                    while self.epg.playService.isWorking() == True and not self.isClosing:
                        xbmc.sleep(100)
                    self.ChannelChanged = 0
                    self.show()
                    self.displayService = True
                else:
                    debug('Pla waitForPlayBackStopped not waiting anymore')
                    self.wait = False
                    break

        self.onPlayBackStopped()

    def _channelUp(self):
        #debug('Pla _channelUp')
        channel = self.database.getNextChannel(self.epg.currentChannel)
        self.playChannel(channel)

    def _channelDown(self):
        #debug('Pla _channelDown')
        channel = self.database.getPreviousChannel(self.epg.currentChannel)
        self.playChannel(channel)

    def playChannel(self, channel):
        debug('Pla playChannel')
        if channel.id != self.epg.currentChannel.id:
            self.ChannelChanged = 1
            self.epg.updateCurrentChannel(channel)
            self.program = self.getCurrentProgram()
            self.epg.program = self.program
            urlList = self.database.getStreamUrlList(channel)
            if len(urlList) > 0:
                self.epg.playService.playUrlList(urlList, resetReconnectCounter=True)
                if self.showOsdOnPlay:
                    self.displayAutoOsd = True

    def changeStream(self):
        deb('Changing stream for channel %s' % self.epg.currentChannel.id)
        self.epg.playService.playNextStream()
        self.displayService = True
        if ADDON.getSetting('osd_on_stream_change') == 'true':
            self.displayAutoOsd = True

    def getProgramUp(self, program):
        channel = self.database.getPreviousChannel(program.channel)
        return self.database.getCurrentProgram(channel)

    def getProgramDown(self, program):
        channel = self.database.getNextChannel(program.channel)
        return self.database.getCurrentProgram(channel)

    def getProgramLeft(self, program):
        return self.database.getPreviousProgram(program)

    def getProgramRight(self, program):
        return self.database.getNextProgram(program)

    def getCurrentProgram(self):
        return self.database.getCurrentProgram(self.epg.currentChannel)

    def showVidOsd(self, action = None):
        self.program = self.getCurrentProgram()
        self.displayServiceOnOSD()
        self.videoOSD = VideoOSD(self, False, action)
        self.videoOSD.doModal()
        del self.videoOSD
        self.videoOSD = None

    def closeOSD(self):
        #debug('Pla closeOSD')
        self.isClosing = True
        if self.videoOSD:
            self.videoOSD.isClosing = True
            self.videoOSD.close()
        if self.displayServiceTimer:
            self.displayServiceTimer.cancel()
        self.close()

    def displayServiceOnOSD(self):
        #debug('displayServiceOnOSD')
        self.displayService = False
        if self.ctrlService and ADDON.getSetting('show_service_name') == 'true':
            displayedService = self.epg.playService.getCurrentServiceString()
            self.ctrlService.setLabel(displayedService)
            if self.displayServiceTimer:
                self.displayServiceTimer.cancel()
            self.displayServiceTimer = threading.Timer(3, self.hideServiceOnOSD)
            self.displayServiceTimer.start()

    def hideServiceOnOSD(self):
        self.displayServiceTimer = None
        self.ctrlService.setLabel('')

    def getControl(self, controlId):
        try:
            return super(Pla, self).getControl(controlId)
        except:
            pass
        return None

class ProgramListDialog(xbmcgui.WindowXMLDialog):
    C_PROGRAM_LIST = 1000
    C_PROGRAM_LIST_TITLE = 1001

    def __new__(cls, title, programs, currentChannel, sort_time=False):
        return super(ProgramListDialog, cls).__new__(cls, 'script-tvguide-programlist.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, title, programs, currentChannel, sort_time=False):
        super(ProgramListDialog, self).__init__()
        self.title = title
        self.programs = programs
        self.index = -1
        self.action = None
        self.sort_time = sort_time
        self.startChannelIndex = currentChannel

    def onInit(self):       
        control = self.getControl(ProgramListDialog.C_PROGRAM_LIST_TITLE)
        control.setLabel(self.title)

        items = list()
        index = 0

        for program in self.programs:  # type: object
            label = program.title
            description = program.description
            descriptionParser = src.ProgramDescriptionParser(description)
            se_label = " %s" % descriptionParser.extractEpisode()
            try:
                episode = program.episode
                if episode:
                    se_label = "%s" % (episode)
            except:
                pass
            label = label + se_label
            name = ""
            icon = program.channel.logo  # type: object
            item = xbmcgui.ListItem(label, name, icon)

            item.setProperty('index', str(index))
            index = index + 1

            item.setProperty('ChannelName', replace_formatting(program.channel.title))
            item.setProperty('Plot', replace_formatting(program.description))
            item.setProperty('startDate', str(time.mktime(program.startDate.timetuple())))

            start = program.startDate
            end = program.endDate
            duration = end - start
            now = datetime.datetime.now()

            if now > start:
                when = datetime.timedelta(-1)
                elapsed = now - start
            else:
                when = start - now
                elapsed = datetime.timedelta(0)

            day = self.formatDateTodayTomorrow(start)
            start_str = start.strftime("%H:%M")
            start_str = "%s %s" % (start_str,day)
            item.setProperty('StartTime', start_str)

            duration_str = "%d min" % (duration.seconds / 60)
            item.setProperty('Duration', duration_str)

            days = when.days
            hours, remainder = divmod(when.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 1:
                when_str = strings(30332).encode('utf-8') % (days)
                item.setProperty('When', when_str)
            elif days > 0:
                when_str = strings(30333).encode('utf-8') % (days)
                item.setProperty('When', when_str)
            elif hours > 1:
                when_str = strings(30334).encode('utf-8') % (hours)
                item.setProperty('When', when_str)
            elif seconds > 0:
                when_str = strings(30335).encode('utf-8') % (when.seconds / 60)
                item.setProperty('When', when_str)

            if elapsed.seconds > 0:
                progress = 100.0 * float(timedelta_total_seconds(elapsed)) / float(duration.seconds+0.001)
                progress = str(int(progress))
            else:
                #TODO hack for progress bar with 0 time
                progress = "0"

            if progress and (int(progress) < 100):
                item.setProperty('Completed', progress)

            program_image = program.imageSmall if program.imageSmall else program.imageLarge
            item.setProperty('ProgramImage', program_image)
            items.append(item)

        if self.sort_time == True:
            items = sorted(items, key=lambda x: x.getProperty('startDate'))

        listControl = self.getControl(ProgramListDialog.C_PROGRAM_LIST)
        listControl.addItems(items)
        listControl.selectItem(int(self.startChannelIndex))

    def onAction(self, action):
        listControl = self.getControl(self.C_PROGRAM_LIST)
        self.id = self.getFocusId(self.C_PROGRAM_LIST)
        item = listControl.getSelectedItem()
        if item:
            self.index = int(item.getProperty('index'))
        else:
            self.index = -1
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK]:
            self.action = KEY_NAV_BACK
            self.close()
        elif action.getId() == KEY_CONTEXT_MENU:
            self.action = KEY_CONTEXT_MENU
            self.close()
        elif action.getId() == ACTION_LEFT:
            self.action = ACTION_LEFT
            self.close()
        elif action.getId() == ACTION_RIGHT:
            self.action = ACTION_RIGHT
            self.close()
        elif action.getId() == ACTION_SHOW_INFO:
            self.action = ACTION_SHOW_INFO
            self.close()

    def onClick(self, controlId):
        if controlId == self.C_PROGRAM_LIST:
            listControl = self.getControl(self.C_PROGRAM_LIST)
            self.id = self.getFocusId(self.C_PROGRAM_LIST)
            item = listControl.getSelectedItem()
            if item:
                self.index = int(item.getProperty('index'))
            else:
                self.index = -1
            self.close()

    def onFocus(self, controlId):
        pass

    #TODO make global function
    def formatDateTodayTomorrow(self, timestamp):
        if timestamp:
            today = datetime.datetime.today()
            tomorrow = today + datetime.timedelta(days=1)
            yesterday = today - datetime.timedelta(days=1)
            if today.date() == timestamp.date():
                return strings(30329).encode('utf-8')
            elif tomorrow.date() == timestamp.date():
                return strings(30330).encode('utf-8')
            elif yesterday.date() == timestamp.date():
                return strings(30331).encode('utf-8')
            else:
                return timestamp.strftime("%A")

    def close(self):
        super(ProgramListDialog, self).close()