#      Copyright (C) 2016 Andrzej Mleczko

import os, threading, datetime, subprocess, unicodedata, time, re, copy
import xbmcgui, xbmc
from strings import *
import strings as strings2
from playService import BasePlayService
import serviceLib
import ConfigParser
from skins import Skin

recordIcon = 'recordIcon.png'
recordNotificationName          = strings(69004).encode('utf-8')
finishedRecordNotificationName  = strings(69005).encode('utf-8')
nonExistingRecordDirName        = strings(69006).encode('utf-8')
failedRecordDialogName          = strings(69007).encode('utf-8')
missingRecordBinaryString       = strings(69008).encode('utf-8')

maxNrOfReattempts               = int(ADDON.getSetting('max_reattempts'))
minRecordedFileSize             = 4097152 #Less then 4MB, remove downloaded data

ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
KEY_NAV_BACK = 92

try:
    config = ConfigParser.RawConfigParser()
    config.read(os.path.join(Skin.getSkinPath(), 'settings.ini'))
    skin_resolution = config.getboolean("Skin", "resolution")
except:
    skin_resolution = '720p'

class RecordTimer:
    def __init__(self, startDate, startOffset, timer, programList):
        self.startDate = startDate
        self.startOffset = startOffset
        self.timer = timer
        self.programList = programList

class RecordService(BasePlayService):
    def __init__(self, epg):
        BasePlayService.__init__(self)
        self.rtmpdumpExe        = xbmc.translatePath(ADDON.getSetting('rtmpdumpExe'))
        self.ffmpegdumpExe      = xbmc.translatePath(ADDON.getSetting('ffmpegExe'))
        self.rtmpdumpAvailable  = os.path.isfile(self.rtmpdumpExe)
        self.ffmpegdumpAvailable= os.path.isfile(self.ffmpegdumpExe)
        self.useOnlyFFmpeg      = ADDON.getSetting('use_only_ffmpeg')
        self.recordDestinationPath = xbmc.translatePath(ADDON.getSetting('record.folder'))
        self.icon               = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('path')), recordIcon)
        self.epg                = epg
        self.threadList         = list()
        self.timers             = list()
        self.cleanupTimer       = None
        self.ffmpegFormat       = 'mpegts'
        if ADDON.getSetting('ffmpeg_dis_cop_un') == 'true':
            self.ffmpegDisableCopyUnknown = True
        else:
            self.ffmpegDisableCopyUnknown = False

        if 'avconv' in self.ffmpegdumpExe:
            self.force_h264_mp4toannexb = True
        else:
            self.force_h264_mp4toannexb = False

        if ADDON.getSetting('record_stop_playback') == 'true':
            self.recordingStopsPlayback = True
        else:
            self.recordingStopsPlayback = False


    def recordProgramGui(self, program):
        updateDB = False
        try:
            if self.calculateTimeDifference(program.endDate) <= 0:
                deb('recordProgramGui - not trying to record since program already finished!')
                return False

            if self.isProgramScheduled(program):
                ret = xbmcgui.Dialog().yesno(heading=strings(69000).encode('utf-8'), line1=strings(69009).encode('utf-8'), autoclose=60000)
                if ret == True:
                    self.epg.database.removeRecording(program)
                    self.cancelProgramRecord(program)
                    updateDB = True
            elif program.recordingScheduled != 1:
                recordMenu = RecordMenu(program)
                recordMenu.doModal()
                saveRecording, startOffset, endOffset = recordMenu.getOffsets()

                if saveRecording == True:
                    startOffset *= 60
                    endOffset *= 60
                    if self.scheduleRecording(program, startOffset, endOffset):
                        self.epg.database.addRecording(program, startOffset, endOffset)
                        updateDB = True
            else:
                self.epg.database.removeRecording(program)
                updateDB = True

        except:
            deb('recordProgramGui exception: %s' % getExceptionString())
        return updateDB


    def scheduleAllRecordings(self):
        deb('scheduleAllRecordings')
        channels = self.epg.database.getChannelList(True)
        for channel_name, program_title, start_date, end_date, start_offset, end_offset in self.epg.database.getRecordings():
            timeDelta = end_date - datetime.datetime.now()
            timeToProgramEnd = timeDelta.seconds + timeDelta.days * 86400
            if timeToProgramEnd < 0:
                debug('scheduleAllRecordings %s has already finished' % program_title)
                continue
            for channel in channels:
                if channel.id == channel_name:
                    program = self.epg.database.getProgramStartingAt(channel, start_date)
                    if program is not None and self.isProgramScheduled(program) == False:
                        self.scheduleRecording(program, start_offset, end_offset, 30)
                    break
        debug('scheduleAllRecordings completed!')


    def scheduleRecording(self, program, startOffset, endOffset, delayRecording = 0):

        program = copy.deepcopy(program)
        program.endDate += datetime.timedelta(seconds=endOffset)
        
        secToFinishRecording = self.calculateTimeDifference(program.endDate, timeOffset = -5 )  #stop 5 sec earlier to release stream and allow recording of next program on that channel
        if secToFinishRecording <= 0:
            deb('RecordService not scheduling record for program %s, starting at %s, ending at %s, since it already finished' % (program.title.encode('utf-8'), program.startDate, program.endDate))
            return False
        else:
            deb('RecordService scheduling record for program %s, starting at %s, start offset %s' % (program.title.encode('utf-8'), program.startDate, startOffset))

        if self.rtmpdumpAvailable == False and self.ffmpegdumpAvailable == False:
            deb('RecordService - no record application installed!')
            self.showThreadedDialog(failedRecordDialogName, "\n" + missingRecordBinaryString)
            return False

        if not self.checkIfRecordDirExist():
            return False

        secToRecording = self.calculateTimeDifference(program.startDate, timeOffset = startOffset + 5 )
        if secToRecording < 0:
            secToRecording = delayRecording   #start now

        for element in self.getScheduledRecordingsForThisTime(program.startDate):
            if element.startOffset == startOffset:
                programList = element.programList    #Fetch already scheduled list of programs
                for prog in programList:
                    if program.channel == prog.channel and program.startDate == prog.startDate:
                        return False        #already on list
                programList.append(program) #add one more
                return True

        programList = list()
        programList.append(program)
        timer = threading.Timer(secToRecording, self.recordChannel, [program.startDate, startOffset])
        self.timers.append(RecordTimer(program.startDate, startOffset, timer, programList))
        timer.start()
        return True


    def recordChannel(self, startTime, startOffset):
        deb('RecordService recordChannel startTime %s, startOffset %s' % (startTime, startOffset))
        for element in self.getScheduledRecordingsForThisTime(startTime):
            if element.startOffset == startOffset:
                programList = element.programList
                self.timers.remove(element)
                for program in programList:
                    urlList = self.epg.database.getStreamUrlList(program.channel)
                    threadData = {'urlList' : urlList, 'program' : program, 'recordHandle' : None, 'stopRecordTimer' : None, 'terminateThread' : False}
                    thread = threading.Thread(name='recordLoop', target = self.recordLoop, args=[threadData])
                    self.threadList.append([thread, threadData])
                    thread.start()


    def recordLoop(self, threadData):

        threadData['success']               = False
        threadData['notificationDisplayed'] = False
        threadData['destinationFile']       = os.path.join(self.recordDestinationPath, self.getOutputFilename(threadData['program']))
        threadData['partNumber']            = 1
        threadData['nrOfReattempts']        = 0
        threadData['recordOptions']         = { 'forceRTMPDump' : False, 'settingsChanged' : False, 'force_h264_mp4toannexb' : self.force_h264_mp4toannexb }
        threadData['recordDuration']        = self.calculateTimeDifference(threadData['program'].endDate, timeOffset = -5 )

        while self.checkIfRecordingShouldContinue(threadData):
            for url in threadData['urlList']:
                if not self.checkIfRecordingShouldContinue(threadData):
                    break

                threadData['recordOptions']['forceRTMPDump'] = False

                self.recordUrl(url, threadData)
                if threadData['recordOptions']['settingsChanged'] == True and self.checkIfRecordingShouldContinue(threadData):
                    deb('RecordService - detected settings change for recorded stream - retrying record')
                    self.recordUrl(url, threadData)

            #Go to sleep, maybe after that any service will be free to use
            for sleepTime in range(5):
                if not self.checkIfRecordingShouldContinue(threadData):
                    break
                time.sleep(1) 

        deb('RecordService - end of recording program: %s' % threadData['program'].title.encode('utf-8', 'ignore'))
        self.showEndRecordNotification(threadData)

        if self.cleanupTimer is not None:
            self.cleanupTimer.cancel()
        self.cleanupTimer = threading.Timer(0.2, self.cleanupFinishedThreads)
        self.cleanupTimer.start()


    def recordUrl(self, url, threadData):
        threadData['recordOptions']['settingsChanged'] = False
        threadData['recordDuration'] = self.calculateTimeDifference(threadData['program'].endDate, timeOffset = -5 )

        if threadData['recordDuration'] <= 0:
            deb('RecordService - recordUrl ducation is 0, aborting record')
            return

        if self.recordingStopsPlayback and (xbmc.Player().isPlaying() or self.epg.playService.isWorking()):
            deb('RecordService - stopping ongoing playback')
            self.epg.playService.stopPlayback()
            xbmc.sleep(500)

        cid, service = self.parseUrl(url)
        channelInfo = self.getChannel(cid, service)

        if channelInfo is None:
            threadData['nrOfReattempts'] += 1
            deb('RecordService recordUrl - locked service %s - trying next, nrOfReattempts: %d, max: %d' % (service, threadData['nrOfReattempts'], maxNrOfReattempts))
            return #go to next stream - this one seems to be locked

        self.findNextUnusedOutputFilename(threadData)
                
        if self.rtmpdumpAvailable and self.useOnlyFFmpeg == 'false' and (channelInfo.rtmpdumpLink is not None or (threadData['recordOptions']['forceRTMPDump'] == True and 'rtmp:' in channelInfo.strm) ):
            recordCommand = self.generateRTMPDumpCommand(channelInfo, threadData['recordDuration'], threadData['destinationFile'], threadData['recordOptions'])
        elif self.ffmpegdumpAvailable:
            recordCommand = self.generateFFMPEGCommand(channelInfo, threadData['recordDuration'], threadData['destinationFile'], threadData['recordOptions'])
        else:
            recordCommand = None
            deb('RecordService recordUrl ERROR, cant choose record application, self.rtmpdumpAvailable: %s, self.ffmpegdumpAvailable: %s, self.useOnlyFFmpeg: %s, channelInfo.rtmpdumpLink: %s, forceRTMPDump: %s, rtmpInUrl: %s' % (self.rtmpdumpAvailable, self.ffmpegdumpAvailable, self.useOnlyFFmpeg, channelInfo.rtmpdumpLink, threadData['recordOptions']['forceRTMPDump'], 'rtmp:' in channelInfo.strm) )

        if recordCommand:
            self.showStartRecordNotification(threadData)
            output = self.record(recordCommand, threadData)
            self.postRecordActions(output, threadData)
        else:
            threadData['nrOfReattempts'] += 1

        self.unlockService(service)


    def record(self, recordCommand, threadData):
        deb('RecordService record command: %s' % str(recordCommand))
        threadData['recordStartTime'] = datetime.datetime.now()
        output = ''
        si = None
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        recordEnviron = os.environ.copy()
        oldLdPath = recordEnviron.get("LD_LIBRARY_PATH", '')
        recordEnviron["LD_LIBRARY_PATH"] = os.path.join(os.path.dirname(recordCommand[0]), 'lib') + ':/lib:/usr/lib:/usr/local/lib'
        if oldLdPath != '':
            recordEnviron["LD_LIBRARY_PATH"] = recordEnviron["LD_LIBRARY_PATH"] + ":" + oldLdPath
        try:
            threadData['stopRecordTimer'] = threading.Timer(threadData['recordDuration'] + 5, self.stopRecord, [threadData])
            threadData['stopRecordTimer'].start()
            threadData['recordHandle'] = subprocess.Popen(recordCommand, shell=False, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=si, env=recordEnviron)
            output = threadData['recordHandle'].communicate()[0]
            returnCode = threadData['recordHandle'].returncode
            threadData['stopRecordTimer'].cancel()
            threadData['recordHandle'] = None
            deb('RecordService record finished, \noutput: %s, \nstatus: %d, Command: %s' % (output, returnCode, str(recordCommand)))
        except Exception, ex:
            deb('RecordService record exception: %s' % getExceptionString())
        return output


    def stopRecord(self, threadData, kill = False):
        if threadData['recordHandle'] is not None:
            try:
                threadData['recordHandle'].terminate()
                #if kill == True:
                    #threadData['recordHandle'].kill()
            except:
                pass


    def postRecordActions(self, recordOutput, threadData):
        self.analyzeRecordOutput(recordOutput, threadData['recordOptions'])
        recordedSecs = (datetime.datetime.now() - threadData['recordStartTime']).seconds
        if(threadData['recordDuration'] - recordedSecs < 60):
            deb('RecordService recordLoop successfully recored program: %s, started at: %s, ended at: %s, duration %d, now: %s' % (threadData['program'].title.encode('utf-8', 'ignore'), threadData['program'].startDate, threadData['program'].endDate, threadData['recordDuration'], datetime.datetime.now()))
            threadData['success'] = True
        else:
            deb('RecordService recordLoop ERROR: too short recording, got: %d sec, should be: %d, program: %s, start at: %s, end at: %s, nrOfReattempts: %d, max: %d' % (recordedSecs, threadData['recordDuration'], threadData['program'].title.encode('utf-8', 'ignore'), threadData['program'].startDate, threadData['program'].endDate, threadData['nrOfReattempts'], maxNrOfReattempts))
            threadData['nrOfReattempts'] += 1
            if os.path.isfile(threadData['destinationFile']) and os.path.getsize(threadData['destinationFile']) < minRecordedFileSize: #Less than minimum, remove downloaded data
                try:
                    deb('RecordService recordLoop deleting incomplete record file %s, recorded for %d s, size %d KB' % (threadData['destinationFile'], recordedSecs, os.path.getsize(threadData['destinationFile'])/1024))
                    os.remove(threadData['destinationFile'])
                except:
                    pass


    def analyzeRecordOutput(self, output, recordOptions):
        try:
            if 'Unrecognized option' in output:
                if 'copy_unknown' in output:
                    deb('RecordService detected problem with copy_unknown - disabling it!')
                    ADDON.setSetting(id="ffmpeg_dis_cop_un", value=str("true"))
                    if self.ffmpegDisableCopyUnknown == False:
                        recordOptions['settingsChanged'] = True
                        self.ffmpegDisableCopyUnknown = True

            if "Detected librtmp style URL parameters, these aren't supported" in output:
                deb('RecordService detected that stream needs to be recorded by RTMPdump')
                if recordOptions['forceRTMPDump'] == False:
                    recordOptions['settingsChanged'] = True
                    recordOptions['forceRTMPDump'] = True

            if "use -bsf h264_mp4toannexb" in output:
                deb('RecordService detected that stream needs to be encoded using h264_mp4toannexb')
                if recordOptions['force_h264_mp4toannexb'] == False:
                    recordOptions['settingsChanged'] = True
                    recordOptions['force_h264_mp4toannexb'] = True
        except:
            pass


    def calculateTimeDifference(self, programTime, timeOffset = 0):
        timeDiff = programTime - datetime.datetime.now()
        programDuration = ((timeDiff.days * 86400) + timeDiff.seconds) + timeOffset
        return programDuration


    def checkIfRecordingShouldContinue(self, threadData):
        return (threadData['success'] == False and threadData['recordDuration'] > 0 and threadData['nrOfReattempts'] <= maxNrOfReattempts and self.terminating == False and threadData['terminateThread'] == False and strings2.M_TVGUIDE_CLOSING == False)


    def generateRTMPDumpCommand(self, channelInfo, programDuration, destinationFile, recordOptions):
        recordCommand = list()
        recordCommand.append(self.rtmpdumpExe)

        if channelInfo.rtmpdumpLink:
            recordCommand.extend(channelInfo.rtmpdumpLink)
        else:
            recordCommand.append("-i")
            recordCommand.append("%s" % channelInfo.strm)
        if os.name != 'nt':
            recordCommand.append("--realtime")
        recordCommand.append("--timeout")
        recordCommand.append("5")
        recordCommand.append("--hashes")
        recordCommand.append("--live")
        recordCommand.append("-B")
        recordCommand.append("%d" % programDuration)
        recordCommand.append("-o")
        recordCommand.append(destinationFile)
        return recordCommand


    def generateFFMPEGCommand(self, channelInfo, programDuration, destinationFile, recordOptions):
        recordCommand = list()
        recordCommand.append(self.ffmpegdumpExe)

        if channelInfo.ffmpegdumpLink is not None:
            recordCommand.extend(channelInfo.ffmpegdumpLink)
        else:
            streamSource = channelInfo.strm
            coockieSeparator = streamSource.find('|')
            if coockieSeparator > 0:
                removedCoockie = streamSource[coockieSeparator+1:]
                streamSource = streamSource[:coockieSeparator]
                deb('RecordService - found coockie separator in record source! Remove this from URL: %s' % removedCoockie)

                headers = removedCoockie.split('&')
                newHeader = ""
                for header in headers:
                    deb('Got: %s' % header)
                    if 'User-Agent' in header:
                        newHeader = newHeader + "User-Agent: %s\r\n" % serviceLib.HOST
                    else:
                        newHeader = newHeader + "%s\r\n" % header

                recordCommand.append("-headers")
                recordCommand.append(newHeader)

            recordCommand.append("-probesize")
            recordCommand.append("50M")

            recordCommand.append("-analyzeduration")
            recordCommand.append("20M")

            recordCommand.append("-i")
            recordCommand.append("%s" % streamSource)

        recordCommand.append("-c")
        recordCommand.append("copy")

        recordCommand.append("-sn")  #Disable subtitles

        recordCommand.append("-map")
        recordCommand.append("0")

        if not self.ffmpegDisableCopyUnknown:
            recordCommand.append("-copy_unknown")

        recordCommand.append("-f")
        recordCommand.append("%s" % self.ffmpegFormat)

        if recordOptions['force_h264_mp4toannexb']:
            recordCommand.append("-bsf")
            recordCommand.append("h264_mp4toannexb")

        recordCommand.append("-t")
        recordCommand.append("%d" % programDuration)
        recordCommand.append("-loglevel")
        recordCommand.append("info")
        recordCommand.append("-n")
        recordCommand.append("%s" % destinationFile)
        return recordCommand


    def showStartRecordNotification(self, threadData):
        if threadData['notificationDisplayed'] == False:
            xbmc.executebuiltin('Notification(%s,%s,10000,%s)' % (recordNotificationName, self.normalizeString(threadData['program'].title), self.icon))
            threadData['notificationDisplayed'] = True #show only once


    def showEndRecordNotification(self, threadData):
        if threadData['notificationDisplayed'] == True:
            xbmc.executebuiltin('Notification(%s,%s,10000,%s)' % (finishedRecordNotificationName, self.normalizeString(threadData['program'].title), self.icon))


    def close(self):
        deb('RecordService close')
        self.terminating = True
        for element in self.timers[:]:
            element.timer.cancel()
        self.timers = list()

        for thread in self.threadList[:]:
            if thread[0].is_alive():
                self.stopRecord(thread[1], kill = True) #stop all recordings
        for thread in self.threadList[:]:
            if thread[0].is_alive():
                thread[0].join(30) #wait for threads to clean up
        self.threadList = list()
        if self.cleanupTimer is not None:
            self.cleanupTimer.cancel()


    def getScheduledRecordingsForThisTime(self, startDate):
        recordings = list()
        for element in self.timers:
            if element.startDate == startDate:
                debug('RecordService getScheduledRecordingsForThisTime found programs starting at %s, startOffset %s' % (startDate, element.startOffset))
                recordings.append(element)

        if len(recordings) == 0:
            debug('RecordService getScheduledRecordingsForThisTime no programs starting at %s' % startDate)
        return recordings


    def normalizeString(self, text):
        nkfd_form = unicodedata.normalize('NFKD', unicode(text))
        text = (u"".join([c for c in nkfd_form if not unicodedata.combining(c)])).encode('ascii', 'ignore')
        return re.compile('[^A-Za-z0-9_]+', re.IGNORECASE).sub('_', text)


    def getOutputFilename(self, program, partNumber = 0):
        filename = self.normalizeString(program.title) + "_" + str(program.startDate.strftime("%Y-%m-%d_%H-%M"))
        if partNumber > 1:
            filename = filename + "_part_%d" % partNumber
        return filename + ".mpeg"


    def findNextUnusedOutputFilename(self, threadData):
        while os.path.isfile(threadData['destinationFile']): #Generate output filename which is not used
            threadData['partNumber'] += 1
            outputFileName = self.getOutputFilename(threadData['program'], threadData['partNumber'])
            threadData['destinationFile'] = os.path.join(self.recordDestinationPath, outputFileName)


    def getListOfFilenamesForProgram(self, program):
        #debug('getListOfFilenamesForProgram')
        filenameList = list()
        filename = self.getOutputFilename(program)
        filePath = os.path.join(self.recordDestinationPath, filename)
        partNumber = 1
        while os.path.isfile(filePath):
            filenameList.append(filePath)
            partNumber = partNumber + 1
            filename = self.getOutputFilename(program, partNumber)
            filePath = os.path.join(self.recordDestinationPath, filename)
        return filenameList


    def isProgramRecorded(self, program):
        #debug('RecordService isProgramRecorded program: %s' % program.title.encode('utf-8'))
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        filenameList = self.getListOfFilenamesForProgram(program)
        for filename in filenameList:
            playlist.add(url=filename)
        if playlist.size() > 0:
            return playlist
        return None


    def isProgramScheduled(self, program):
        if program is None:
            return False
        for element in self.getScheduledRecordingsForThisTime(program.startDate):
            programList = element.programList
            for prog in programList:
                if program.channel == prog.channel:
                    return True

        for thread in self.threadList:
            if not thread[0].is_alive():
                continue
            threadData = thread[1]
            prog = threadData['program'] #program recorded by this thread
            if program.channel == prog.channel and program.startDate == prog.startDate:
                return True
        return False


    def cancelProgramRecord(self, program): #wylaczyc akturalnie nagrywany program?
        for element in self.getScheduledRecordingsForThisTime(program.startDate):
            programList = element.programList
            try:
                for prog in programList:
                    if program.channel == prog.channel:
                        programList.remove(prog)
                        if len(programList) == 0:
                            element.timer.cancel()
                            self.timers.remove(element)
                        debug('RecordService canceled scheduled recording of: %s' % program.title.encode('utf-8'))
                        return
            except:
                pass

        for thread in self.threadList:
            if not thread[0].is_alive():
                continue
            threadData = thread[1]
            prog = threadData['program']
            if program.channel == prog.channel and program.startDate == prog.startDate:
                threadData['terminateThread'] = True
                self.stopRecord(threadData)
                debug('RecordService canceled ongoing recording of: %s' % program.title.encode('utf-8'))
                return


    def cleanupFinishedThreads(self):
        for thread in self.threadList[:]:
            try:
                if not thread[0].is_alive():
                    self.threadList.remove(thread)
            except:
                pass


    def isRecordOngoing(self):
        for thread in self.threadList:
            if thread[0].is_alive():
                return True
        return False


    def isRecordScheduled(self):
        if len(self.timers) > 0:
            return True
        return False


    def removeRecordedProgram(self, program):
        debug('removeRecordedProgram')
        if program is None:
            deb('removeRecordedProgram got faulty program!!!!')

        filenameList = self.getListOfFilenamesForProgram(program)

        for filename in filenameList:
            try:
                os.remove(filename)
                debug('removeRecordedProgram removing %s' % filename)
            except Exception, ex:
                deb('removeRecordedProgram exception: %s' % getExceptionString())

    def checkIfRecordDirExist(self):
        if self.recordDestinationPath == '':
            deb('checkIfRecordDirExist record destination not configured!')
            self.showThreadedDialog(failedRecordDialogName, "\n" + nonExistingRecordDirName)
            return False
        elif os.path.isdir(self.recordDestinationPath) == False:
            try:
                os.makedirs(self.recordDestinationPath)
                #make sure dir was created
                if os.path.isdir(self.recordDestinationPath) == False:
                    deb('checkIfRecordDirExist record destination does not exist after attmept to create! path: %s' % self.recordDestinationPath)
                    self.showThreadedDialog(failedRecordDialogName, "\n" + nonExistingRecordDirName + "\n" + self.recordDestinationPath)
                    return False
            except:
                deb('checkIfRecordDirExist record destination does not exist and cannot be created! path: %s' % self.recordDestinationPath)
                self.showThreadedDialog(failedRecordDialogName, "\n" + nonExistingRecordDirName + "\n" + self.recordDestinationPath)
                return False
        return True

    def showThreadedDialog(self, dialogName, dialogMessage):
        try:
            threading.Timer(0, self.showDialog, [dialogName, dialogMessage]).start()
        except:
            pass

    def showDialog(self, dialogName, dialogMessage):
        xbmcgui.Dialog().ok(dialogName, dialogMessage)


class RecordMenu(xbmcgui.WindowXMLDialog):
    def __new__(cls, program):
        return super(RecordMenu, cls).__new__(cls, 'script-tvguide-record.xml', Skin.getSkinBasePath(), Skin.getSkinName(), skin_resolution)

    def __init__(self, program):
        self.startOffsetLabelId = 501
        self.endOffsetLabelId = 502

        self.startOffsetSliderId = 401
        self.endOffsetSliderId = 402

        self.saveControlId = 301
        self.cancelControlId = 302
        self.resetControlId = 303

        self.startOffsetValue = 0
        self.endOffsetValue = 0

        self.programTitleId = 201
        self.channelId = 202
        self.startHourId = 203
        self.recordDurationId = 204

        self.record = False
        self.program = program

        self.calculatedStartDate = self.program.startDate
        self.calculatedEndDate = self.program.endDate
        super(RecordMenu, self).__init__()

    def onInit(self):
        self.startOffsetLabel = self.getControl(self.startOffsetLabelId)
        self.endOffsetLabel = self.getControl(self.endOffsetLabelId)

        self.startOffsetSlider = self.getControl(self.startOffsetSliderId)
        self.endOffsetSlider = self.getControl(self.endOffsetSliderId)

        self.startHour = self.getControl(self.startHourId)
        self.recordDuration = self.getControl(self.recordDurationId)

        self.getControl(self.programTitleId).setLabel('%s' % self.program.title)
        self.getControl(self.channelId).setLabel('%s' % self.program.channel.title)

        self.resetSliders()

    def resetSliders(self):
        self.startOffsetSlider.setPercent(50)
        self.endOffsetSlider.setPercent(50)
        self.updateLabels()

    def updateLabels(self):
        self.startOffsetValue = int(self.startOffsetSlider.getPercent() - 50)
        self.endOffsetValue = int(self.endOffsetSlider.getPercent() - 50)

        self.startOffsetLabel.setLabel('%s' % self.startOffsetValue)
        self.endOffsetLabel.setLabel('%s' % self.endOffsetValue)

        self.calculatedStartDate = self.program.startDate + datetime.timedelta(minutes=self.startOffsetValue)
        self.calculatedEndDate = self.program.endDate + datetime.timedelta(minutes=self.endOffsetValue)

        self.startHour.setLabel('%s' % self.calculatedStartDate)

        if self.calculatedEndDate > self.calculatedStartDate:
            self.recordDuration.setLabel('%s' % (self.calculatedEndDate - self.calculatedStartDate))
        else:
            self.recordDuration.setLabel('%s' % 0)

    def getOffsets(self):
        if self.calculatedStartDate > self.calculatedEndDate:
            self.record = False
        return [self.record, self.startOffsetValue, self.endOffsetValue]

    def onAction(self, action):
        if action.getId() in [ACTION_PREVIOUS_MENU, KEY_NAV_BACK, ACTION_PARENT_DIR, 101]:
            deb('RecordMenu got action close!')
            self.close()
        else:
            self.updateLabels()

    def onClick(self, controlId):
        if controlId == self.cancelControlId:
            self.close()
        elif controlId == self.resetControlId:
            self.resetSliders()
        elif controlId == self.saveControlId:
            self.record = True
            self.close()
