#      Copyright (C) 2016 Andrzej Mleczko

import re, copy, datetime
from strings import *
from serviceLib import *

serviceName = 'GoldVOD'
#goldUrl = 'http://goldvod.tv/api/get_tv_channels'
goldUrl = 'http://goldvod.tv/api/index.php?page=get_tv_channels'
getChannelUrl = 'http://goldvod.tv/api/index.php?page=get_tv_channel'

class GoldVodUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'goldvodmap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('GoldVOD_enabled')
        self.login              = ADDON.getSetting('usernameGoldVOD')
        self.password           = ADDON.getSetting('userpasswordGoldVOD')
        self.location           = ADDON.getSetting('GoldVOD_location')
        self.servicePriority    = int(ADDON.getSetting('priority_goldvod'))
        self.url                = goldUrl
        self.maxAllowedStreams  = 2
        self.addDuplicatesAtBeginningOfList = True
        self.channelListUpdateTime = None
        self.noPremiumPrinted   = False

        if ADDON.getSetting('assign_all_streams_goldvod') == 'true':
            self.addDuplicatesToList = True


    def getChannelList(self, silent = False):
        if silent is not True:
            self.log('\n\n')
            self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
            self.log('[UPD] -------------------------------------------------------------------------------------')
            self.log('[UPD] %-10s %-35s' % ( '-CID-', '-NAME-'))
        else:
            self.log('Aktualizuje liste kanalow w serwisie %s' % self.serviceName)
        result = list()
        post = { 'login' : self.login, 'pass' : self.password, 'location' : self.location, 'port' : '80'}
        channelsArray = self.sl.getJsonFromAPI(self.url, post)

        if channelsArray is None:
            self.loginErrorMessage()
            return result

        regexReplace = re.compile('SERWER\s*\d*', re.IGNORECASE)

        if len(channelsArray) > 0:
            try:
                for s in range(len(channelsArray)):
                    is_sd = False
                    is_hd = False
                    cid = self.sl.decode(channelsArray[s]['id']).replace("\"", '')
                    ico = self.sl.decode(channelsArray[s]['icon']).replace("\"", '')
                    if len(self.sl.decode(channelsArray[s]['url_sd']).replace("\"", '')) is not 0:
                        is_sd = True
                    try:
                        if len(channelsArray[s]['url_hd']) is not 0 and ADDON.getSetting('video_qualityGoldVOD') == 'true':
                            is_hd = True
                    except:
                        pass
                    name = self.sl.decode(channelsArray[s]['name']).replace("\"", '')
                    name = regexReplace.sub('', name).replace('  ', ' ').strip()

                    if is_sd and (is_hd == False or ADDON.getSetting('assign_all_streams_goldvod') == 'true'):
                        if silent is not True:
                            self.log('[UPD] %-10s %-35s' % (cid + "_SD", name))
                        goldvodProgram = TvCid(cid + "_SD", name, name, '', ico)
                        result.append(goldvodProgram)

                    if is_hd:
                        if silent is not True:
                            self.log('[UPD] %-10s %-35s' % (cid + "_HD", name))
                        goldvodProgram = TvCid(cid + "_HD", name, name, '', ico)
                        result.append(goldvodProgram)

                self.channelListUpdateTime  = datetime.datetime.now()
            except:
                self.log('getChannelList exception while looping channelsArray, error: %s' % getExceptionString())
        else:
            self.log('getChannelList returned empty channel array!!!!!!!!!!!!!!!!')
            self.loginErrorMessage()
        return result

    def getChannelStream(self, chann):
        origCid = chann.cid.replace('_HD', '').replace('_SD', '')
        post = { 'login' : self.login, 'pass' : self.password, 'location': self.location, 'port': '80', 'id': origCid}
        url = None
        channelData = self.sl.getJsonFromAPI(getChannelUrl, post)
        if channelData and channelData['status']:
            if '_HD' in chann.cid:
                url = channelData['url_hd']
                if url is None or url == '':
                    url = channelData['url_sd']
            elif '_SD' in chann.cid:
                url = channelData['url_sd']
        else:
            if not self.noPremiumPrinted:
                self.noPremiumPrinted = True
                xbmcgui.Dialog().notification(strings(SERVICE_ERROR), strings(57039) + ' ' + self.serviceName, time=5000, sound=False)

        if url is not None and url != '':
            chann.strm = url
            chann.rtmpdumpLink = list()
            chann.rtmpdumpLink.append("--rtmp")
            chann.rtmpdumpLink.append("%s" % url)
            self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (chann.cid, chann.name, chann.strm))
            return chann
        
        self.log('getChannelStream could not get RTMP link, channel data: %s' % str(channelData))
        return None