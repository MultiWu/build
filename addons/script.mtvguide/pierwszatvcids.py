#      Copyright (C) 2016 Andrzej Mleczko

import copy, datetime, base64
import xbmc, xbmcgui
from strings import *
from serviceLib import *

serviceName = 'PierwszaTV'
baseUrl     = 'http://pierwsza.tv/'
lo          = 'VzRaQS0+PC1iMGZjZTI4NzlhM2Q0MDYwNzQ2YTI1Zjc1ZDUwZGFkZQ=='

class PierwszaTvUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'pierwszatvmap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('pierwszatv_enabled')
        self.login              = ADDON.getSetting('pierwszatv_username').strip()
        self.password           = ADDON.getSetting('pierwszatv_password').strip()
        self.servicePriority    = int(ADDON.getSetting('priority_pierwszatv'))
        self.url                = baseUrl
        self.refreshTimer       = None
        self.timerData          = {}
        self.addDuplicatesToList = True

    def getChannelList(self, silent = False):
        if silent is not True:
            self.log('\n\n')
            self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
            self.log('[UPD] -------------------------------------------------------------------------------------')
            self.log('[UPD] %-10s %-35s' % ( '-CID-', '-NAME-'))
        result = list()

        tmp_data = base64.b64decode(lo).split('-><-')
        self.apiId = tmp_data[0]
        self.apiChecksum = tmp_data[1]
        channelsArray = self.sl.getJsonFromExtendedAPI(self.url + 'api/channels?api_id=%s&checksum=%s' % (self.apiId, self.apiChecksum), jsonLoadsResult=True)

        try:
            if channelsArray is None or channelsArray['status'] != 'ok':
                try:
                    self.log('getChannelList error while downloading channnel list, message: %s' % channelsArray['message'])
                except:
                    self.log('getChannelList error while downloading channnel list, no response!')
                channelsArray = list()
            else:
                channelsArray = channelsArray['channels']
        except:
            self.log('getChannelList Exception: %s' % getExceptionString())
            return result


        if len(channelsArray) > 0:
            try:
                for s in range(len(channelsArray)):
                    cid = self.sl.decode(channelsArray[s]['id']).replace("\"", '').strip()
                    ico = channelsArray[s]['thumbail']
                    if ico:
                        ico = baseUrl + self.sl.decode(ico).replace("\"", '').strip()
                    else:
                        ico = ''
                    name = self.sl.decode(channelsArray[s]['name']).replace("\"", '').strip()

                    self.log('[UPD] %-10s %-35s' % (cid, name))

                    program = TvCid(cid, name, name, '', ico)
                    result.append(program)
            except:
                self.log('getChannelList exception while looping channelsArray, error: %s' % getExceptionString())
        else:
            self.log('getChannelList returned empty channel array!!!!!!!!!!!!!!!!')
            self.loginErrorMessage()
        return result

    def getChannelStream(self, chann):

        channelData = self.sl.getJsonFromExtendedAPI(self.url + 'api/stream/create?api_id=%s&checksum=%s&id=%s&user=%s&password=%s' % (self.apiId, self.apiChecksum, chann.cid, self.login, self.password), jsonLoadsResult=True)
        self.log('getChannelStream stream/create URL returned: %s' % str(channelData))

        if not channelData or channelData['status'] != 'ok':
            self.log('Error while trying to get channel data: %s' % str(channelData))
            if channelData and channelData['message']:
                xbmcgui.Dialog().notification(strings(SERVICE_ERROR), channelData['message'] + ' ' + self.serviceName, time=10000, sound=False)
            return None

        serverId = channelData['serverId']
        token = channelData['token']
        streamId = channelData['streamId']
        tokenExpireIn = int(channelData['tokenExpireIn'])

        startTime = datetime.datetime.now()
        while (datetime.datetime.now() - startTime).seconds < 30 and strings2.M_TVGUIDE_CLOSING == False:
            serverStatus = self.sl.getJsonFromExtendedAPI(self.url + 'api/stream/status?api_id=%s&checksum=%s&serverId=%s&streamId=%s' % (self.apiId, self.apiChecksum, serverId, streamId), jsonLoadsResult=True)
            self.log('getChannelStream stream/status URL returned: %s' % str(serverStatus))

            if not serverStatus or serverStatus['status'] != 'ok' or serverStatus['sourceError'] == True:
                self.log('getChannelStream error while trying to get server status: %s' % str(serverStatus))
                return None

            if serverStatus['started'] == True:
                self.unlockService()
                timeDifference = (datetime.datetime.now() - startTime).seconds
                refreshTokenIn = int(tokenExpireIn * 0.75) - timeDifference
                if refreshTokenIn < 1:
                    refreshTokenIn = 1
                self.log('getChannelStream cid: %s - stream ready after %d seconds! Refreshing token in %s seconds.' % (chann.cid, timeDifference, refreshTokenIn))
                self.timerData = { 'terminate' : False, 'serverId' : serverId, 'streamId' : streamId, 'token' : token }
                self.refreshTimer = threading.Timer(refreshTokenIn, self.refreshToken, args=[self.timerData])
                self.refreshTimer.start()
                break
            else:
                self.log('getChannelStream cid: %s - waiting for server to start stream' % chann.cid)
                xbmc.sleep(150)

        if serverStatus['started'] == False:
            self.log('getChannelStream cid: %s - stream not ready - aborting!' % chann.cid)
            return None

        chann.strm = serverStatus['source'] + '?token=' + token
        self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (chann.cid, chann.name, chann.strm))
        return chann

    def refreshToken(self, timerData):
        if not timerData['terminate']:
            refreshData = self.sl.getJsonFromExtendedAPI(self.url + 'api/stream/refresh?api_id=%s&checksum=%s&serverId=%s&streamId=%s&token=%s' % (self.apiId, self.apiChecksum, timerData['serverId'], timerData['streamId'], timerData['token']), jsonLoadsResult=True)
            self.log('refreshToken stream/refresh URL returned: %s' % str(refreshData))

            if not timerData['terminate'] and refreshData and refreshData['status'] == 'ok':
                refreshTokenIn = int(int(refreshData['tokenExpireIn']) * 0.75)
                self.refreshTimer = threading.Timer(refreshTokenIn, self.refreshToken, args=[timerData])
                self.refreshTimer.start()
            elif not timerData['terminate'] and refreshData:
                self.log('Problem while refreshing token, data sent is: %s' % str(timerData))

    def unlockService(self):
        self.log('unlockService')
        self.timerData['terminate'] = True
        if self.refreshTimer:
            self.refreshTimer.cancel()
