#      Copyright (C) 2016 Andrzej Mleczko

import urllib, copy
import xbmcgui
from strings import *
from serviceLib import *

serviceName = 'WeebTV'
url        = 'http://weeb.tv'
jsonUrl    = url + '/api/getChannelList'
playerUrl  = url + '/api/setPlayer'


class WeebTvCid(TvCid):
    def __init__(self, cid, name, title, online, strm = "", img = "", multibitrate = '0', origCid = 0):
        TvCid.__init__(self, cid, name, title, strm, img)
        self.multibitrate = multibitrate
        self.online = online
        self.origCid = origCid


class WeebTvStrmUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'weebtvmap.xml'
        baseServiceUpdater.__init__(self)
        self.login              = ADDON.getSetting('username')
        self.password           = ADDON.getSetting('userpassword')
        self.highQuality        = ADDON.getSetting('video_quality')
        self.serviceEnabled     = ADDON.getSetting('WeebTV_enabled')
        self.servicePriority    = int(ADDON.getSetting('priority_weebtv'))
        self.url                = jsonUrl
        self.addDuplicatesToList = True
        self.shownNoPremiumNotification = False
        self.premium = 1
        if ADDON.getSetting('miltisession_enabled') == 'true':
            self.maxAllowedStreams = 4
        self.playbackStartTime = None
        self.superviseBlockedWeebTimer = None
        self.blockWeebNextTime  = False
        self.blocked            = False

    def getChannelList(self, silent):
        self.log('\n\n')
        self.log('[UPD] Pobieram liste dostepnych kanalow Weeb.tv z %s' % self.url)
        self.log('[UPD] -------------------------------------------------------------------------------------')
        self.log('[UPD] %-15s %-35s %-30s' % ('-CID-', '-NAME-', '-TITLE-'))
        result = list()
        post = { 'username': self.login, 'userpassword': self.password }
        tmpChannels = self.sl.getJsonFromAPI(self.url, post)

        if tmpChannels is None:
            self.log('getChannelList: Error while loading getJsonFromAPI Url: %s - aborting' % self.url)
            self.loginErrorMessage()
            return result

        channelsArray = self.sl.JsonToSortedTab(tmpChannels)
        if len(channelsArray) > 0:
            try:
                if channelsArray[0][1] == 'Null' or channelsArray[0][1] == 'Error':
                    self.log('getChannelList channelsArray content is: %s' % channelsArray[0][1])
                    self.noPremiumMessage()
                else:
                    for i in range(len(channelsArray)):
                        k = channelsArray[i][1]
                        name    = self.sl.decode(k['channel_name']).replace("\"", '')
                        cid     = self.sl.decode(k['cid']).replace("\"", '')
                        title   = self.sl.decode(k['channel_title']).replace("\"", '').replace(" SD", '').strip()
                        #if len(title) == 0 or title == 'null':
                            #title = name
                        image   = k['channel_logo_url'].replace("\"", '')
                        mbitrate = '0'
                        if self.highQuality == 'true':
                            mbitrate = k['multibitrate']
                        online = k['channel_online']

                        if mbitrate != '0':
                            self.log('[UPD] %-15s %-35s %-30s' % (cid + '_HD', name, title))
                            result.append(WeebTvCid(cid + '_HD', name, title, online, img=image, multibitrate=mbitrate, origCid=cid))
                        if mbitrate == '0' or ADDON.getSetting('assign_all_streams_weeb') == 'true':
                            self.log('[UPD] %-15s %-35s %-30s' % (cid + '_SD', name, title))
                            result.append(WeebTvCid(cid + '_SD', name, title, online, img=image, multibitrate='0', origCid=cid))

            except:
                self.log('getChannelList exception while looping channelsArray, error: %s' % getExceptionString())
        else:
            self.log('getChannelList returned empty channel array!!!!!!!!!!!!!!!!')
            self.noPremiumMessage()
        return result

    def getChannelStream(self, channel):
        try:
            if self.isWeebBlocked():
                return None

            post = { 'cid' : channel.origCid, 'platform' : 'XBMC', 'username' : self.login, 'userpassword' : self.password }
            params = self.sl.getJsonFromExtendedAPI(playerUrl, post_data = post)
            if params == None:
                self.log('updateChannelRTMP failed to fetch channel data')
                return None

            pairParams = (params.replace('?', '')).split('&')
            param = {}
            for i in range(len(pairParams)):
                splitparams = pairParams[i].split('=')
                if (len(splitparams)) == 2:
                    param[int(splitparams[0].strip())] = urllib.unquote_plus(splitparams[1])

            rtmpLink = param[10]
            playPath = param[11]
            ticket = param[73]

            if channel.multibitrate != '0':
                playPath = playPath + 'HI'

            channel.strm = str(rtmpLink) + '/' + str(playPath) + ' swfUrl='  + str(ticket) + ' pageUrl=token' + ' live=true'
            self.premium = int(param[5])
            channel.rtmpdumpLink = list()
            channel.rtmpdumpLink.append("--rtmp")
            channel.rtmpdumpLink.append("%s/%s"  % (str(rtmpLink), str(playPath)) )
            channel.rtmpdumpLink.append("-s")
            channel.rtmpdumpLink.append("%s" % str(ticket))
            channel.rtmpdumpLink.append("-p")
            channel.rtmpdumpLink.append("token")

            self.log('updateChannelRTMP generated RTMP is %s' % channel.strm)
            if not self.shownNoPremiumNotification and self.premium == 0:
                self.noPremiumMessage()
                self.shownNoPremiumNotification = True

            #if self.isWeebBlocked():
                #return None
        except:
            self.log('updateChannelRTMP exception: %s' % getExceptionString())
            return None

        self.playbackStartTime = datetime.datetime.now()
        self.log('getChannelStream found matching channel: cid: %s, name: %s title: %s' % (channel.cid, channel.name, channel.title))
        return channel

    def isWeebBlocked(self):
        try:
            if self.premium == 0:
                if self.blocked:
                    self.log('WeebTV is blocked!')
                    xbmcgui.Dialog().notification(strings(SERVICE_ERROR), self.serviceName + " " + strings(58011) + "!", time=5000, sound=False)
                    return True
                data = self.sl.getJsonFromExtendedAPI(url + '/contact', max_conn_time=3)
                if data:
                    if 'icon online red' in data:
                        self.log('WeebTV is blocking no premium!')
                        return True
        except:
            pass
        return False

    def unlockService(self):
        if self.premium == 0 and self.playbackStartTime:
            if self.superviseBlockedWeebTimer:
                self.superviseBlockedWeebTimer.cancel()

            self.blocked = False
            playbackDuration = (datetime.datetime.now() - self.playbackStartTime).seconds
            self.log('Playback stopped after %s seconds' % playbackDuration )
            if playbackDuration < 6:
                if self.blockWeebNextTime:
                    self.log('Blocking WeebTV!')
                    self.blocked = True
                    self.superviseBlockedWeebTimer = threading.Timer(600, self.resetBlockedStatus)
                    self.superviseBlockedWeebTimer.start()
                else:
                    self.log('Next time WeebTV will be blocked!')
                self.blockWeebNextTime = True
            else:
                self.blockWeebNextTime = False

    def resetBlockedStatus(self):
        self.log('Unblocking WeebTV!')
        self.blocked = False
        
    def close(self):
        if self.superviseBlockedWeebTimer:
            self.superviseBlockedWeebTimer.cancel()
        baseServiceUpdater.close(self)
                    
    def resetService(self):
        if self.superviseBlockedWeebTimer:
            self.superviseBlockedWeebTimer.cancel()
        self.blocked = False
        self.blockWeebNextTime = False
        baseServiceUpdater.resetService(self)