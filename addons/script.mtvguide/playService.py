#      Copyright (C) 2016 Andrzej Mleczko

import xbmcgui, xbmc, datetime, threading
from strings import *
import strings as strings2
import serviceLib

import weebtvcids
import goldvodcids
import playlistcids
#import pierwszatvcids
import wizjatvcids
#import yoytvcids
import videostarcids
import iplacids

SERVICES = {
    weebtvcids.serviceName          : weebtvcids.WeebTvStrmUpdater(),
    goldvodcids.serviceName         : goldvodcids.GoldVodUpdater(),
    playlistcids.serviceName + '_1' : playlistcids.PlaylistUpdater(instance_number=1),
    playlistcids.serviceName + '_2' : playlistcids.PlaylistUpdater(instance_number=2),
    playlistcids.serviceName + '_3' : playlistcids.PlaylistUpdater(instance_number=3),
    playlistcids.serviceName + '_4' : playlistcids.PlaylistUpdater(instance_number=4),
    playlistcids.serviceName + '_5' : playlistcids.PlaylistUpdater(instance_number=5),
#    pierwszatvcids.serviceName      : pierwszatvcids.PierwszaTvUpdater(),
    wizjatvcids.serviceName         : wizjatvcids.WizjaTVUpdater(),
#    yoytvcids.serviceName           : yoytvcids.YoyTVUpdater(),
    videostarcids.serviceName       : videostarcids.VideoStarUpdater(),
    iplacids.serviceName            : iplacids.IplaUpdater()
}

for serviceName in SERVICES.keys():
    if SERVICES[serviceName].serviceEnabled != 'true':
        SERVICES[serviceName].close()
        del SERVICES[serviceName]

class BasePlayService:
    lockMap = {}
    maxAllowedStreams = {}
    lock = threading.Lock()
    for service in SERVICES:
        lockMap[service] = 0
        maxAllowedStreams[service] = SERVICES[service].maxAllowedStreams

    def __init__(self):
        self.thread = None
        self.terminating = False
        self.starting = False

    def parseUrl(self, url):
        cid = 0
        service = None
        try:
            params = url[8:].split('&')
            service = params[0]
            cid = params[1].split('=')[1]
            deb(self.__class__.__name__ + ' parseUrl: cid %s, service %s' % (cid, service))
        except:
            pass
        return [cid, service]

    def isWorking(self):
        if self.thread is not None:
            return self.thread.is_alive() or self.starting
        return False

    def getChannel(self, cid, service, currentlyPlayedService = { 'service' : None }):
        BasePlayService.lock.acquire() # make this function thread safe
        channelInfo = None
        if self.isServiceLocked(service) == True and service != currentlyPlayedService['service']: #if issued by PlayService and it's the same as played then allow using the same service - it will be release anyway
            deb(self.__class__.__name__ + ' getChannel service %s is locked - aborting' % service)
            BasePlayService.lock.release()
            return None
        try:
            serviceHandler = SERVICES[service]
        except KeyError:
            serviceHandler = None

        if serviceHandler is not None:
            channelInfo = serviceHandler.getChannel(cid)

        if channelInfo is not None and service != currentlyPlayedService['service']:
            self.lockService(service)
        BasePlayService.lock.release()
        return channelInfo

    def lockService(self, service):
        try:
            BasePlayService.lockMap[service] = BasePlayService.lockMap[service] + 1
            deb(self.__class__.__name__ + ' lockService: %d streams handled by service: %s, max is: %d' % (BasePlayService.lockMap[service], service, BasePlayService.maxAllowedStreams[service]))
        except:
            pass

    def unlockService(self, service):
        try:
            if service:
                BasePlayService.lockMap[service] = BasePlayService.lockMap[service] - 1
                SERVICES[service].unlockService()
                deb(self.__class__.__name__ + ' unlockService: still %d streams handled by service: %s, max is: %d' % (BasePlayService.lockMap[service], service, BasePlayService.maxAllowedStreams[service]))
                if BasePlayService.lockMap[service] < 0:
                    deb(self.__class__.__name__ + ' error while unlocking service, nr less than 0, something went wrong!')
                    raise
        except:
            pass

    def isServiceLocked(self, service):
        try:
            if BasePlayService.lockMap[service] >= BasePlayService.maxAllowedStreams[service]:
                return True
        except:
            pass
        return False

class PlayService(xbmc.Player, BasePlayService):
    def __init__(self, *args, **kwargs):
        BasePlayService.__init__(self)
        self.playbackStopped        = False
        self.playbackStarted        = False
        self.currentlyPlayedService = { 'service' : None }
        self.urlList                = None
        self.playbackStartTime      = None
        self.sleepSupervisor        = serviceLib.SleepSupervisor(self.stopPlayback)
        self.streamQuality          = ''
        self.userStoppedPlayback    = True
        self.nrOfResumeAttempts     = 0
        self.threadData             = { 'terminate' : False }
        self.maxNrOfResumeAttempts  = int(ADDON.getSetting('max_reconnect_attempts'))
        self.reconnectDelay         = int(ADDON.getSetting('reconnect_delay'))
        self.reconnectFailedStreams = ADDON.getSetting('reconnect_stream')
        self.maxStreamStartupTime   = int(ADDON.getSetting('max_wait_for_playback')) * 10
        

    def playUrlList(self, urlList, resetReconnectCounter=False):
        if urlList is None or len(urlList) == 0:
            deb('playUrlList got empty list to play - aborting!')
            self.starting = False
            return
        self.starting = True
        self.threadData['terminate'] = True
        currentThreadData = self.threadData = { 'terminate' : False }
        if resetReconnectCounter:
            self.nrOfResumeAttempts = 0

        if self.thread is not None and self.thread.is_alive():
            deb('PlayService playUrlList waiting for thread to terminate')
            self.terminating = True
            while self.thread is not None and self.thread.is_alive() and currentThreadData['terminate'] == False:
                xbmc.sleep(100)

        if currentThreadData['terminate'] == True:
            deb('playUrlList decided to terminate thread starting playback')
            return

        self.thread = threading.Thread(name='playUrlList Loop', target = self._playUrlList, args=[urlList])
        self.thread.start()
        self.starting = False

    def _playUrlList(self, urlList):
        self.terminating = False
        self.urlList = list(urlList)
        self.userStoppedPlayback = False

        for url in self.urlList[:]:
            if self.userStoppedPlayback or self.terminating or strings2.M_TVGUIDE_CLOSING:
                deb('_playUrlList aborting loop, self.userStoppedPlayback: %s, self.terminating: %s' % (self.userStoppedPlayback, self.terminating))
                return

            playStarted, customPlugin = self.playUrl(url)

            if not playStarted:
                deb('_playUrlList playback not started - checking next stream')
            else:

                if customPlugin:
                    waitTime = self.maxStreamStartupTime + 30
                else:
                    waitTime = self.maxStreamStartupTime

                start_date = datetime.datetime.now()
                for i in range(waitTime):

                    if self.terminating == True or strings2.M_TVGUIDE_CLOSING == True or self.userStoppedPlayback:
                        if strings2.M_TVGUIDE_CLOSING == True:
                            self.userStoppedPlayback = True
                            xbmc.Player().stop()
                        self.unlockCurrentlyPlayedService()
                        deb('PlayService _playUrlList abort requested - terminating')
                        return

                    if self.playbackStarted == True:
                        deb('PlayService _playUrlList detected stream start!')
                        self.playbackStartTime = datetime.datetime.now()
                        return

                    if self.playbackStopped == True or playStarted == False:
                        break

                    if i == (waitTime - 1):
                        deb('PlayService _playUrlList maximum wait time (%s) for stream start exceeded! Time since starting stream: %s' % (waitTime, (datetime.datetime.now() - start_date).seconds))

                    xbmc.sleep(100)

                deb('PlayService _playUrlList detected faulty stream! playbackStopped: %s, playStarted: %s' % (self.playbackStopped, playStarted) )
                self.unlockCurrentlyPlayedService()
                xbmc.Player().stop()

            try:
                #move stream to the end of list
                self.urlList.remove(url)
                self.urlList.append(url)
            except Exception, ex:
                deb('_playUrlList exception: %s' % getExceptionString())

        deb('PlayService _playUrlList non of streams started - stopping playback!')
        self.userStoppedPlayback = True
        xbmc.Player().stop()


    def playUrl(self, url):
        self.playbackStopped = False
        self.playbackStarted = False
        self.streamQuality = ''
        success = True
        customPlugin = False

        if url[-5:] == '.strm':
            try:
                f = open(url)
                content = f.read()
                f.close()
                if content[0:9] == 'plugin://':
                    url = content.strip()
            except:
                pass

        if url[0:9] == 'plugin://':
            self.unlockCurrentlyPlayedService()
            if ADDON.getSetting('start_video_minimalized') == 'true':
                xbmc.executebuiltin('PlayMedia(%s, false, 1)' % url)
            else:
                xbmc.executebuiltin('PlayMedia(%s)' % url)
            customPlugin = True
        elif url[0:7] == 'service':
            cid, service = self.parseUrl(url)
            success = self.LoadVideoLink(cid, service)
            if success:
                self.getStreamQualityFromCid(cid)
        else:
            self.unlockCurrentlyPlayedService()
            xbmc.Player().play(url)
        return [success, customPlugin]

    def playNextStream(self):
        if self.urlList and len(self.urlList) > 1:
            tmpUrl = self.urlList.pop(0)
            self.urlList.append(tmpUrl)
            debug('PlayService playNextStream skipping: %s, next: %s' % (tmpUrl, self.urlList[0]))
            self.playUrlList(self.urlList)

    def LoadVideoLink(self, channel, service):
        #deb('LoadVideoLink %s service' % service)
        res = False
        channels = None
        startWindowed = False
        if ADDON.getSetting('start_video_minimalized') == 'true':
            startWindowed = True

        channelInfo = self.getChannel(channel, service, self.currentlyPlayedService)

        if channelInfo is not None:
            if self.currentlyPlayedService['service'] != service:
                self.unlockCurrentlyPlayedService()
            self.currentlyPlayedService['service'] = service

            if self.terminating or self.userStoppedPlayback:
                deb('LoadVideoLink aborting playback: self.terminating %s, self.userStoppedPlayback: %s' % (self.terminating, self.userStoppedPlayback))
                self.unlockCurrentlyPlayedService()
                return res

            liz = xbmcgui.ListItem(channelInfo.title, iconImage = channelInfo.img, thumbnailImage = channelInfo.img)
            liz.setInfo( type="Video", infoLabels={ "Title": channelInfo.title, } )
            try:
                self.playbackStopped = False
                xbmc.Player().play(channelInfo.strm, liz, windowed=startWindowed)
                res = True
            except Exception, ex:
                deb('Exception while trying to play video: %s' % getExceptionString())
                self.unlockCurrentlyPlayedService()
                xbmcgui.Dialog().ok(strings(57018).encode('utf-8'), strings(57021).encode('utf-8') + '\n' + strings(57028).encode('utf-8') + '\n' + str(ex))
        else:
            deb('LoadVideoLink ERROR channelInfo is None! service: %s' % service)
        return res

    def onPlayBackStopped(self):
        self.playbackStopped = True
        self.unlockCurrentlyPlayedService()
        self.sleepSupervisor.Stop()
        self.tryResummingPlayback()

    def onPlayBackEnded(self):
        self.playbackStopped = True
        self.unlockCurrentlyPlayedService()
        self.sleepSupervisor.Stop()
        self.tryResummingPlayback()

    def onPlayBackStarted(self):
        self.playbackStarted = True
        self.sleepSupervisor.Start()

    def stopPlayback(self):
        debug('PlayService stopPlayback')
        self.urlList = None
        self.userStoppedPlayback = True
        self.nrOfResumeAttempts = 0
        self.terminating = True
        self.unlockCurrentlyPlayedService()
        try:
            xbmc.Player().stop()
        except:
            xbmc.executebuiltin('PlayerControl(Stop)')

    def unlockCurrentlyPlayedService(self):
        if self.currentlyPlayedService['service'] is not None:
            self.unlockService(self.currentlyPlayedService['service'])
            self.currentlyPlayedService['service'] = None

    def getStreamQualityFromCid(self, cid):
        #debug('getStreamQualityFromCid cid: %s' % cid)
        self.streamQuality = ''
        try:
            parts = cid.split("_")
            self.streamQuality = parts[1]
        except:
            pass

    def tryResummingPlayback(self):
        deb('PlayService tryResummingPlayback self.userStoppedPlayback: %s, self.isWorking(): %s, self.nrOfResumeAttempts: %s, self.maxNrOfResumeAttempts: %s' % (self.userStoppedPlayback, self.isWorking(), self.nrOfResumeAttempts, self.maxNrOfResumeAttempts))
        if self.isWorking() == False and self.urlList is not None and self.userStoppedPlayback == False and self.reconnectFailedStreams == 'true':
            if self.nrOfResumeAttempts < self.maxNrOfResumeAttempts:
                self.nrOfResumeAttempts += 1
                self.starting = True
                deb('PlayService reconnecting, nr of reattempts: %s' % self.nrOfResumeAttempts)
                if self.playbackStartTime is not None and (datetime.datetime.now() - self.playbackStartTime).seconds < 10:
                    try:
                        #Playback didn't last for 10s - remove stream from list
                        deb('Playback last for only %s seconds - moving to next one' % (datetime.datetime.now() - self.playbackStartTime).seconds)
                        self.urlList.pop(0)
                    except Exception, ex:
                        deb('tryResummingPlayback exception: %s' % getExceptionString())
                if self.urlList is not None and len(self.urlList) > 0:
                    if self.reconnectDelay > 0:
                        xbmc.sleep(self.reconnectDelay)
                    self.playUrlList(self.urlList)
                else:
                    deb('tryResummingPlayback empty playback list, cant resume!')
                    self.starting = False
            else:
                deb('PlayService reached reconnection limit - aborting!')
                self.stopPlayback()



    def getCurrentServiceString(self):
        service = ''
        if self.currentlyPlayedService['service'] is not None:
            service = self.currentlyPlayedService['service']
            try:
                serviceHandler = SERVICES[service]
                service = serviceHandler.getDisplayName()
            except:
                pass
            if self.streamQuality != '':
                service = service + ' ' + self.streamQuality.upper()
        return service

    def close(self):
        self.terminating = True
        self.stopPlayback()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(10)
        for serviceName in SERVICES:
            SERVICES[serviceName].close()
