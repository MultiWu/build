#
#      Copyright (C) 2018 Mariusz Brychcy
#      Copyright (C) 2013 Szakalit
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
import datetime, time, re, os, threading
import xbmc, xbmcgui
import ConfigParser
from strings import *
from skins import Skin
from source import Program, Channel

config = ConfigParser.RawConfigParser()
config.read(os.path.join(Skin.getSkinPath(), 'settings.ini'))
try:
    skin_resolution = config.getboolean("Skin", "resolution")
except:
    skin_resolution = '720p'

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
ACTION_SHOW_UP = 16
ACTION_SHOW_DOWN = 17

C_MAIN_CHAN_NAME = 4919
C_MAIN_TITLE = 4920
C_MAIN_TIME = 4921
C_MAIN_DESCRIPTION = 4922
C_MAIN_IMAGE = 4923
C_MAIN_CHAN_NUMBER = 4925
C_MAIN_START_TIME = 4950
C_MAIN_END_TIME = 4951
C_MAIN_CHAN_PLAY = 4952
C_MAIN_PROG_PLAY = 4953
C_MAIN_TIME_PLAY = 4954
C_MAIN_NUMB_PLAY = 4955
C_MAIN_CALC_TIME = 4956
C_MAIN_NEXT_PROGRAM = 4957
C_MAIN_CALC_TIME_LEFT = 4958
C_MAIN_CALC_TIME_PASS = 4959
C_STOP = 101
C_SHOW_INFO = 102
C_PAGE_DOWN = 103
C_PAGE_UP = 104
C_PLAY = 105
C_SETUP = 106
C_SCHEDULE = 107
C_UNSCHEDULE = 108
C_SUBS = 109
C_LANG = 110
C_ACTION_RIGHT = 111
C_ACTION_BACK = 112
C_ACTION_NUMBER = 113
C_CLOSE_WINDOW = 1000
C_VIDEO_OSD_WINDOW = 100

ACTION_MOUSE_WHEEL_UP = 104
ACTION_MOUSE_WHEEL_DOWN = 105
ACTION_MOUSE_MOVE = 107

KEY_NAV_BACK = 92
KEY_CONTEXT_MENU = 117
KEY_HOME = 159
AUTO_OSD = 666

try:
     KEY_STOP = int(ADDON.getSetting('stop_key'))
except:
     KEY_STOP = -1
try:
     KEY_CONTEXT = int(ADDON.getSetting('context_key'))
except:
     KEY_CONTEXT = -1
try:
     KEY_INFO = int(ADDON.getSetting('info_key'))
except:
     KEY_INFO = -1
try:
     KEY_SWITCH_TO_LAST = int(ADDON.getSetting('switch_to_last_key'))
except:
     KEY_SWITCH_TO_LAST = -1
try:
     KEY_PP = int(ADDON.getSetting('pp_key'))
except:
     KEY_PP = 0
try:
     KEY_PM = int(ADDON.getSetting('pm_key'))
except:
     KEY_PM = 0

class VideoOSD(xbmcgui.WindowXMLDialog):
    def __new__(cls, gu, controlledByMouse = True, action = None):
        return super(VideoOSD, cls).__new__(cls, 'VidOSD.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, gu, controlledByMouse = True, action = None):
        self.gu = gu
        self.playService = self.gu.epg.playService
        self.isClosing = False
        self.mouseCount = 0
        self.program = self.gu.program
        self.controlledByMouse = controlledByMouse
        self.keyRightLeftChangeProgram = False
        self.showConfigButtons = False
        self.initialized = False
        self.osdDisplayTime = int(ADDON.getSetting('osd_time'))
        self.blockOsd = False
        self.channelIdx = 0
        self.timer = None
        self.channel_number_input = False
        self.channel_number = ADDON.getSetting('channel.arg')
        if ADDON.getSetting('show_osd_buttons') == 'true':
            self.showConfigButtons = True
        if not self.showConfigButtons and ADDON.getSetting('key_right_left_show_next') == 'true':
            self.keyRightLeftChangeProgram = True

        if action is not None:
            if action == ACTION_UP:
                self.program = self.gu.getProgramUp(self.program)
            elif action == ACTION_DOWN:
                self.program = self.gu.getProgramDown(self.program)
            elif action == ACTION_LEFT:
                self.showPreviousProgram()
            elif action == ACTION_RIGHT:
                self.showNextProgram()
            elif action == AUTO_OSD:
                self.osdDisplayTime = int(ADDON.getSetting('osd_on_play_time'))
            if not self.program:
                self.program = self.gu.getCurrentProgram()

        self.ignoreMissingControlIds = list()
        self.ignoreMissingControlIds.append(C_MAIN_START_TIME)
        self.ignoreMissingControlIds.append(C_MAIN_END_TIME)
        self.ignoreMissingControlIds.append(C_MAIN_CHAN_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_PROG_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_TIME_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_NUMB_PLAY)
        self.ignoreMissingControlIds.append(C_MAIN_CALC_TIME)
        self.ignoreMissingControlIds.append(C_MAIN_CALC_TIME_LEFT)
        self.ignoreMissingControlIds.append(C_MAIN_CALC_TIME_PASS)
        self.ignoreMissingControlIds.append(C_MAIN_NEXT_PROGRAM)

        super(VideoOSD, self).__init__()

    def onInit(self):
        if not self.controlledByMouse:
            closeWindowControl = self.getControl(C_CLOSE_WINDOW)
            closeWindowControl.setVisible(False)
            closeWindowControl.setEnabled(False)
            threading.Timer(1, self.waitForKeyboard).start()
        else:
            threading.Timer(1, self.waitForMouse).start()

        self.playControl = self.getControl(C_PLAY)
        self.stopPlaybackControl = self.getControl(C_STOP)
        self.pageUpControl = self.getControl(C_PAGE_UP)
        self.pageDownControl = self.getControl(C_PAGE_DOWN)
        self.infoControl = self.getControl(C_SHOW_INFO)
        self.setupControl = self.getControl(C_SETUP)
        self.nextSubtitle = self.getControl(C_SUBS)
        self.audioNextLanguage = self.getControl(C_LANG)
        self.scheduleControl = self.getControl(C_SCHEDULE)
        self.unscheduleControl = self.getControl(C_UNSCHEDULE)
        self.videoOsdWindowControl = self.getControl(C_VIDEO_OSD_WINDOW)
        self.actionback = self.getControl(C_ACTION_BACK)
        self.actionright = self.getControl(C_ACTION_RIGHT)
        self.actionnumber = self.getControl(C_ACTION_NUMBER)

        if self.controlledByMouse or self.showConfigButtons:
            self.infoControl.controlRight(self.setupControl)
            self.setupControl.controlLeft(self.infoControl)
            self.setupControl.controlRight(self.nextSubtitle)
            self.pageDownControl.controlLeft(self.actionright)
            self.pageDownControl.controlRight(self.pageUpControl)
            self.pageUpControl.controlLeft(self.pageDownControl)
            self.stopPlaybackControl.controlLeft(self.pageUpControl)
            self.stopPlaybackControl.controlRight(self.infoControl)
            self.playControl.controlRight(self.infoControl)
            self.playControl.controlLeft(self.pageUpControl)
            self.scheduleControl.controlRight(self.infoControl)
            self.scheduleControl.controlLeft(self.pageUpControl)
            self.unscheduleControl.controlRight(self.infoControl)
            self.unscheduleControl.controlLeft(self.pageUpControl)
            self.nextSubtitle.controlLeft(self.setupControl)
            self.nextSubtitle.controlRight(self.audioNextLanguage)
            self.audioNextLanguage.controlLeft(self.nextSubtitle)
            self.audioNextLanguage.controlRight(self.actionnumber)
            self.actionnumber.controlLeft(self.audioNextLanguage)
            self.actionnumber.controlRight(self.actionback)
            self.actionback.controlLeft(self.actionnumber)
            self.actionback.controlRight(self.actionright)
            self.actionright.controlLeft(self.actionback)
            self.actionright.controlRight(self.pageDownControl)
        else:
            self.pageUpControl.setVisible(False)
            self.pageDownControl.setVisible(False)
            self.infoControl.setVisible(False)
            self.setupControl.setVisible(False)
            self.nextSubtitle.setVisible(False)
            self.audioNextLanguage.setVisible(False)
            self.actionnumber.setVisible(False)
            self.actionback.setVisible(False)
            self.actionright.setVisible(False)
            self.pageUpControl.setEnabled(False)
            self.pageDownControl.setEnabled(False)
            self.infoControl.setEnabled(False)
            self.setupControl.setEnabled(False)
            self.nextSubtitle.setEnabled(False)
            self.audioNextLanguage.setEnabled(False)
            self.actionnumber.setEnabled(False)
            self.actionback.setEnabled(False)
            self.actionright.setEnabled(False)
            self.unscheduleControl.setVisible(True)
            self.unscheduleControl.setEnabled(True)

        self.playControl.setVisible(False)
        self.stopPlaybackControl.setVisible(False)
        self.scheduleControl.setVisible(False)
        self.actionback.setVisible(True)
        self.actionright.setVisible(True)
        self.stopPlaybackControl.setEnabled(False)
        self.playControl.setEnabled(True)
        self.scheduleControl.setEnabled(False)
        self.unscheduleControl.setVisible(False)
        self.unscheduleControl.setEnabled(False)


        self.ctrlServiceName    = self.getControl(C_MAIN_SERVICE_NAME)
        self.ctrlChanName       = self.getControl(C_MAIN_CHAN_NAME)
        self.ctrlChanNamePlay       = self.getControl(C_MAIN_CHAN_PLAY)
        self.ctrlProgNamePlay       = self.getControl(C_MAIN_PROG_PLAY)
        self.ctrlMainTitle      = self.getControl(C_MAIN_TITLE)
        self.ctrlProgramTitle   = self.getControl(C_MAIN_TITLE)
        self.ctrlProgramTime    = self.getControl(C_MAIN_TIME)
        self.ctrlProgramTimePlay    = self.getControl(C_MAIN_TIME_PLAY)
        self.ctrlStartProgramTime    = self.getControl(C_MAIN_START_TIME)
        self.ctrlEndProgramTime    = self.getControl(C_MAIN_END_TIME)
        self.ctrlCalcProgramTime    = self.getControl(C_MAIN_CALC_TIME)
        self.ctrlCalcProgramTimeLeft    = self.getControl(C_MAIN_CALC_TIME_LEFT)
        self.ctrlCalcProgramTimePass    = self.getControl(C_MAIN_CALC_TIME_PASS)
        self.ctrlNextProgram    = self.getControl(C_MAIN_NEXT_PROGRAM)
        self.ctrlProgramDesc    = self.getControl(C_MAIN_DESCRIPTION)
        self.ctrlProgramLogo    = self.getControl(C_MAIN_LOGO)
        self.ctrlProgramImg     = self.getControl(C_MAIN_IMAGE)
        self.ctrlMainLive       = self.getControl(C_MAIN_LIVE)
        self.ctrlProgramSlider = self.getControl(C_PROGRAM_SLIDER)
        self.ctrlProgramProgress = self.getControl(C_PROGRAM_PROGRESS)
        self.ctrlChanNumber     = self.getControl(C_MAIN_CHAN_NUMBER)
        self.ctrlChanNumberPlay    = self.getControl(C_MAIN_NUMB_PLAY)

        self.mousetime = time.mktime(datetime.datetime.now().timetuple())
        self.keyboardTime = time.mktime(datetime.datetime.now().timetuple())
        threading.Timer(1, self.waitForPlayBackStopped).start()

        self.initialized = True
        self.refreshControls()

    def setControlVisibility(self):
        currentlyPlayedProgram = self.gu.getCurrentProgram()
        timeDiff = self.program.startDate - datetime.datetime.now()
        secToStartProg = (timeDiff.days * 86400) + timeDiff.seconds

        self.playControl.setVisible(False)
        self.stopPlaybackControl.setVisible(False)
        self.scheduleControl.setVisible(False)
        self.unscheduleControl.setVisible(False)
        self.playControl.setEnabled(False)
        self.stopPlaybackControl.setEnabled(False)
        self.scheduleControl.setEnabled(False)
        self.unscheduleControl.setEnabled(False)

        if secToStartProg > 0:
            #Future program, not started yet
            if ADDON.getSetting('notifications.enabled') == 'true':
                if not self.gu.epg.notification.isScheduled(self.program):
                    self.scheduleControl.setVisible(True)
                    self.scheduleControl.setEnabled(True)
                    self.infoControl.controlLeft(self.scheduleControl)
                    self.pageUpControl.controlRight(self.scheduleControl)
                    self.setFocusIfNeeded(C_SCHEDULE)
                else:
                    self.infoControl.controlLeft(self.unscheduleControl)
                    self.pageUpControl.controlRight(self.unscheduleControl)
                    self.unscheduleControl.setVisible(True)
                    self.unscheduleControl.setEnabled(True)
                    self.setFocusIfNeeded(C_UNSCHEDULE)
            else:
                self.infoControl.controlLeft(self.pageUpControl)
                self.pageUpControl.controlRight(self.infoControl)
                self.setFocusIfNeeded(C_PLAY)

        elif not self.controlledByMouse and not (currentlyPlayedProgram.channel.id == self.program.channel.id and currentlyPlayedProgram.startDate == self.program.startDate):
            #Program executed on different channel than currently is on, False if mouse controlled
            self.playControl.setEnabled(True)
            self.playControl.setVisible(True)
            self.infoControl.controlLeft(self.playControl)
            self.pageUpControl.controlRight(self.playControl)
            self.setFocusIfNeeded(C_PLAY)

        elif self.controlledByMouse or self.showConfigButtons:
            self.stopPlaybackControl.setEnabled(True)
            self.stopPlaybackControl.setVisible(True)
            self.infoControl.controlLeft(self.stopPlaybackControl)
            self.pageUpControl.controlRight(self.stopPlaybackControl)
            self.setFocusIfNeeded(C_STOP)

    def setFocusIfNeeded(self, controlId):
        if self.controlledByMouse:
            return
        try:
            currFocus = self.getFocus()
            currFocusVisible = xbmc.getCondVisibility("Control.IsVisible(%s)" % currFocus.getId())
            if not currFocusVisible or currFocus.getId() == controlId:
                self.setFocusId(controlId)
        except:
            self.setFocusId(controlId)

    def playShortcut(self):
        self.channel_number_input = False
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes=self.viewStartDate.minute % 30,
                                                 seconds=self.viewStartDate.second)
        channelList = self.gu.database.getChannelList(onlyVisible=True)
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
        self.gu.playChannel(program.channel)
        self.isClosing = True

    def onAction(self, action):
        debug('VideoOSD onAction keyId %d, buttonCode %d' % (action.getId(), action.getButtonCode()))
        self.keyboardTime = time.mktime(datetime.datetime.now().timetuple())

        if action.getId() in [ACTION_PREVIOUS_MENU, KEY_NAV_BACK, ACTION_PARENT_DIR, 101]:
            self.isClosing = True

        if action.getId() in [ACTION_STOP] or action.getButtonCode() == KEY_STOP:
            self.isClosing = True
            self.playService.stopPlayback()

        elif action.getId() == ACTION_MOUSE_MOVE:
            self.mouseCount = self.mouseCount + 1
            if self.mouseCount > 2:
                self.mouseCount =  0
                self.mousetime = time.mktime(datetime.datetime.now().timetuple())
                #self.refreshControls()

        elif action.getId() == KEY_CONTEXT_MENU or action.getButtonCode() == KEY_CONTEXT:
            self.isClosing = True
            self.gu.changeStream()

        elif self.controlledByMouse:
            return #remaining are for keyboard

        elif (action.getId() == ACTION_UP):
            self.program = self.gu.getProgramUp(self.program)
            self.refreshControls()

        elif (action.getId() == ACTION_DOWN):
            self.program = self.gu.getProgramDown(self.program)
            self.refreshControls()

        elif (action.getId() == ACTION_LEFT):
            if not self.showConfigButtons:
                self.showPreviousProgram()

        elif (action.getId() == ACTION_RIGHT):
            if not self.showConfigButtons:
                self.showNextProgram()

        elif (action.getId() == ACTION_SELECT_ITEM):
            currentlyPlayedProgram = self.gu.getCurrentProgram()
            if not self.showConfigButtons and currentlyPlayedProgram.channel.id == self.program.channel.id and currentlyPlayedProgram.startDate == self.program.startDate:
                self.isClosing = True

        elif action.getId() == ACTION_SHOW_INFO or action.getButtonCode() == KEY_INFO or action.getId() == KEY_INFO:
            try:
                self.blockOsd = True
                self.videoOsdWindowControl.setVisible(False)
                d = xbmcgui.Dialog()
                list = d.select(strings(31009).encode('utf-8', 'replace'), [strings(58000).encode('utf-8', 'replace'), strings(30356).encode('utf-8', 'replace')])
                if list == 0:
                    self.gu.epg.Info(self.program)
                elif list == 1:
                    self.gu.epg.ExtendedInfo(self.program)
            except:
                pass
            self.keyboardTime = time.mktime(datetime.datetime.now().timetuple())
            self.videoOsdWindowControl.setVisible(True)
            self.blockOsd = False

        elif action.getButtonCode() == KEY_SWITCH_TO_LAST:
            self.isClosing = True
            self.gu.onAction(action)

        elif action.getId() == ACTION_PAGE_UP or (action.getButtonCode() == KEY_PP and KEY_PP != 0) or (action.getId() == KEY_PP and KEY_PP != 0):
            self.program = self.gu.getProgramDown(self.program)
            self.refreshControls()
            xbmc.executebuiltin('Action(Select)')

        elif action.getId() == ACTION_PAGE_DOWN or (action.getButtonCode() == KEY_PM and KEY_PM != 0) or (action.getId() == KEY_PM and KEY_PM != 0):
            self.program = self.gu.getProgramUp(self.program)
            self.refreshControls()
            xbmc.executebuiltin('Action(Select)')

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
                    xbmcgui.Dialog().notification(strings(30353).encode('UTF-8'), strings(30354).encode('UTF-8'))
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
                        xbmcgui.Dialog().notification(strings(30353).encode('UTF-8'), strings(30354).encode('UTF-8'))
                        return

    def showNextProgram(self):
        program = self.gu.getProgramRight(self.program)
        if program is not None:
            self.program = program
            self.refreshControls()

    def showPreviousProgram(self):
        program = self.gu.getProgramLeft(self.program)
        if program is not None:
            timeDiff = program.endDate - datetime.datetime.now()
            diffSec = (timeDiff.days * 86400) + timeDiff.seconds
            if diffSec > 0:
                self.program = program
                self.refreshControls()


    def onClick(self, controlId):
        self.keyboardTime = time.mktime(datetime.datetime.now().timetuple())

        if controlId == 1000:
            self.isClosing = True
        elif controlId == C_STOP:
            self.isClosing = True
            self.gu.onAction2(ACTION_STOP)
        elif controlId == C_PLAY:
            self.isClosing = True
            self.gu.playChannel(self.program.channel)
        elif controlId == C_SHOW_INFO:
            #self.isClosing = False
            self.gu.onAction2(ACTION_SHOW_INFO, self.program)
        elif controlId == C_SETUP:
            self.isClosing = True
            xbmc.executebuiltin('ActivateWindow(videoosd)')
        elif controlId == C_SUBS:
            self.isClosing = False
            xbmc.executebuiltin('Action(NextSubtitle)')
        elif controlId == C_LANG:
            self.isClosing = False
            xbmc.executebuiltin('Action(AudioNextLanguage)')
        elif controlId == C_ACTION_BACK:
            self.isClosing = False
            self.showPreviousProgram()
        elif controlId == C_ACTION_RIGHT:
            self.isClosing = False
            self.showNextProgram()
        elif controlId == C_ACTION_NUMBER:
            if ADDON.getSetting('channel.shortcut') == 'false':
                xbmcgui.Dialog().notification(strings(30353).encode('UTF-8'), strings(30354).encode('UTF-8'))
            else:
                if ADDON.getSetting('channel.shortcut') == 'true':
                    d = xbmcgui.Dialog()
                    number = d.input(strings(30346).encode('utf-8'),type=xbmcgui.INPUT_NUMERIC)
                    if number:
                        self.channel_number = number
                        if self.timer and self.timer.is_alive():
                            self.timer.cancel()
                        self.playShortcut()
        else:
            if self.controlledByMouse:
                self.onClickMouse(controlId)
            else:
                self.onClickKeyboard(controlId)

    def onClickMouse(self, controlId):
        if controlId == C_PAGE_DOWN:
            self.isClosing = True
            self.gu.onAction2(ACTION_PAGE_DOWN)
        elif controlId == C_PAGE_UP:
            self.isClosing = True
            self.gu.onAction2(ACTION_PAGE_UP)

    def onClickKeyboard(self, controlId):
        if controlId == C_PAGE_DOWN:
            self.showPreviousProgram()
            self.setFocusId(C_PAGE_DOWN)
        elif controlId == C_PAGE_UP:
            self.showNextProgram()
            self.setFocusId(C_PAGE_UP)
        elif controlId == C_SCHEDULE:
            if self.gu.epg.notification:
                self.gu.epg.notification.addNotification(self.program, onlyOnce = True)
                self.refreshControls()
        elif controlId == C_UNSCHEDULE:
            if self.gu.epg.notification:
                self.gu.epg.notification.removeNotification(self.program)
                self.refreshControls()

    def refreshControls(self):
        if not self.initialized:
            return

        if self.ctrlServiceName is not None and ADDON.getSetting('show_service_name') == 'true':
            self.ctrlServiceName.setLabel('%s' % self.playService.getCurrentServiceString())
        if self.ctrlChanName is not None:
            self.ctrlChanName.setLabel('%s' % (self.program.channel.title))
        if self.ctrlChanNamePlay is not None:
            self.ctrlChanNamePlay.setLabel('%s' % (self.program.channel.title))
        if self.ctrlProgNamePlay is not None:
            self.ctrlProgNamePlay.setLabel('%s' % (self.program.title))
        if self.ctrlMainTitle is not None:
            self.ctrlMainTitle.setLabel('%s' % (self.program.title))
        if self.ctrlProgramTime is not None:
            self.ctrlProgramTime.setLabel('%s - %s' % (self.formatTime(self.program.startDate), self.formatTime(self.program.endDate)))
        if self.ctrlProgramTimePlay is not None:
            self.ctrlProgramTimePlay.setLabel('%s - %s' % (self.formatTime(self.program.startDate), self.formatTime(self.program.endDate)))
        if self.ctrlStartProgramTime is not None:
            self.ctrlStartProgramTime.setLabel('%s' % (self.formatTime(self.program.startDate)))
        if self.ctrlEndProgramTime is not None:
            self.ctrlEndProgramTime.setLabel('%s' % (self.formatTime(self.program.endDate)))

        if self.ctrlCalcProgramTime is not None:
            start_date = datetime.datetime.now() - self.program.startDate
            end_date = datetime.datetime.now() - self.program.endDate
            self.ctrlCalcProgramTime.setLabel('%s' % (start_date - end_date))

        if self.ctrlCalcProgramTimeLeft is not None:
            prog_time = self.gu.getCurrentProgram().endDate - datetime.datetime.now() 
            prog_time = re.sub(r':\d+\.\d+', '', str(prog_time))
            self.ctrlCalcProgramTimeLeft.setLabel('%s' % (prog_time))
            if xbmc.getCondVisibility('Control.HasFocus(111)'):
                self.ctrlCalcProgramTimeLeft.setLabel('%s' % str('0:00'))

        if self.ctrlCalcProgramTimePass is not None:
            prog_time = datetime.datetime.now() - self.gu.getCurrentProgram().startDate
            prog_time = re.sub(r':\d+\.\d+', '', str(prog_time))
            self.ctrlCalcProgramTimePass.setLabel('%s' % (prog_time))
            if xbmc.getCondVisibility('Control.HasFocus(111)'):
                self.ctrlCalcProgramTimePass.setLabel('%s' % str('0:00'))

        if self.ctrlNextProgram is not None:
            programs = self.gu.database.getNextProgram(self.program)
            for program in [programs]:
                title = program.title
                self.ctrlNextProgram.setLabel('%s' % (title))

        if self.ctrlProgramDesc is not None:
            if self.program.description and self.ctrlProgramDesc:
                self.ctrlProgramDesc.setText(self.program.description)
            else:
                self.ctrlProgramDesc.setText(strings(NO_DESCRIPTION))

        if self.program.channel.logo and self.ctrlProgramLogo:
            self.ctrlProgramLogo.setImage(self.program.channel.logo.encode('utf-8'))

        if self.program.imageSmall is not None and self.ctrlProgramImg:
            self.ctrlProgramImg.setImage(self.program.imageSmall.encode('utf-8'))
        else:
            if self.ctrlProgramImg is not None:
                self.ctrlProgramImg.setImage('tvguide-logo-epg.png')

        if self.program.imageLarge == 'live' and self.ctrlMainLive:
            self.ctrlMainLive.setImage('live.png')
        else:
            if self.ctrlMainLive is not None:
                self.ctrlMainLive.setImage('')

        if self.ctrlProgramSlider:
            self.stdat = time.mktime(self.program.startDate.timetuple())
            self.endat = time.mktime(self.program.endDate.timetuple())
            self.nodat = time.mktime(datetime.datetime.now().timetuple())
            try:
                self.per =  100 -  ((self.endat - self.nodat)/ ((self.endat - self.stdat)/100))
            except:
                self.per = 0
            if self.per > 0 and self.per < 100:
                self.ctrlProgramSlider.setVisible(True)
                self.ctrlProgramSlider.setPercent(self.per)
            else:
                self.ctrlProgramSlider.setVisible(False)

        if self.ctrlProgramProgress:
            self.stdat = time.mktime(self.program.startDate.timetuple())
            self.endat = time.mktime(self.program.endDate.timetuple())
            self.nodat = time.mktime(datetime.datetime.now().timetuple())
            try:
                self.per =  100 -  ((self.endat - self.nodat)/ ((self.endat - self.stdat)/100))
            except:
                self.per = 0
            if self.per > 0 and self.per < 100:
                self.ctrlProgramProgress.setVisible(True)
                self.ctrlProgramProgress.setPercent(self.per)
            else:
                self.ctrlProgramProgress.setVisible(False)

        if (ADDON.getSetting('channel.shortcut') != 'false'):
            if self.ctrlChanNumber is not None:
               self.ctrlChanNumber.setLabel('%s' % (self.gu.database.getCurrentChannelIdx(self.program.channel) + 1))
            if self.ctrlChanNumberPlay is not None:
               self.ctrlChanNumberPlay.setLabel('%s' % (self.gu.database.getCurrentChannelIdx(self.program.channel) + 1))

        self.setControlVisibility()

    def getControl(self, controlId):
        try:
            return super(VideoOSD, self).getControl(controlId)
        except:
            pass
        return None

    def onPlayBackStopped(self):
        self.close()

    def waitForPlayBackStopped(self):
        while xbmc.Player().isPlaying() and not self.isClosing:
            time.sleep(0.1)
        self.onPlayBackStopped()

    def waitForMouse(self):
        while time.mktime(datetime.datetime.now().timetuple()) < self.mousetime + self.osdDisplayTime and not self.isClosing:
            time.sleep(0.1)
        self.isClosing = True

    def waitForKeyboard(self):
        while (time.mktime(datetime.datetime.now().timetuple()) < self.keyboardTime + self.osdDisplayTime or self.blockOsd) and not self.isClosing:
            time.sleep(0.1)
        self.isClosing = True

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

    def close(self):
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        super(VideoOSD, self).close()