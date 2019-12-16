#      Copyright (C) 2016 Andrzej Mleczko

import os, re, copy
import xbmc, xbmcgui
from strings import *
from serviceLib import *

serviceName         = 'WizjaTV'
wizjaUrl            = 'http://wizja.tv/'
COOKIE_FILE         = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('profile')) , 'wizjatv.cookie')

class WizjaTVUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'wizjatvmap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('wizjatv_enabled')
        self.login              = ADDON.getSetting('wizjatv_username').strip()
        self.password           = ADDON.getSetting('wizjatv_password').strip()
        self.servicePriority    = int(ADDON.getSetting('priority_wizjatv'))
        self.useFreeAccount     = ADDON.getSetting('wizjatv_use_free_account')
        self.url                = wizjaUrl
        self.printedError       = False
        self.gotPremium         = False

    def loginService(self):
        post = {}
        post['login']='zaloguj'
        post['user_name'] = self.login
        post['user_password'] = self.password
        data = self.sl.getJsonFromExtendedAPI(self.url + 'users/index.php', post_data = post, cookieFile = COOKIE_FILE, save_cookie = True)
        if not data:
            self.loginErrorMessage()
            return False

        if 'Zarejestruj nowe konto' in data or 'Brak premium' in data:
            if self.useFreeAccount == 'false':
                self.log('No premium in service %s, returned login data is: %s' % (self.serviceName, str(data)))
                self.noPremiumMessage()
                return False
        else:
            self.gotPremium = True

        return True

    def getChannelList(self, silent):
        result = list()
        self.log('\n\n')
        self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
        self.log('[UPD] -------------------------------------------------------------------------------------')
        self.log('[UPD] %-10s %-35s %-35s' % ( '-CID-', '-NAME-', '-IMG-'))

        try:
            if not self.loginService():
                return result
            httpdata = self.sl.getJsonFromExtendedAPI(self.url, cookieFile = COOKIE_FILE, load_cookie = True)
            if not httpdata:
                self.log('Returned httpdata is empty!')
                xbmcgui.Dialog().notification(strings(SERVICE_ERROR), strings(SERVICE_NO_PREMIUM) + ' ' + self.serviceName, time=15000, sound=False)
                return result
            
            data = self.sl.parseDOM(httpdata, 'td')
            for i in data:
                try:
                    try:
                        res = [(self.sl.parseDOM(i, 'a', ret='href')[0], self.sl.parseDOM(i, 'img', ret='src')[0])]
                    except:
                        continue
                    img = (self.url + res[0][1]).encode('utf-8')
                    cid = (res[0][0].replace('watch.php?id=', '').replace('http://wizja.tv/', '')).encode('utf-8')
                    if not cid.isdigit():
                        self.log('Error parsing channel, cid is not a digit! Row: %s' % i)
                        continue
                    name = (res[0][1].replace('ch_logo/', '').replace('.png', '')).encode('utf-8').replace('_black', '')
                    self.log('[UPD] %-10s %-35s %-35s' % (cid, name, img))
                    program = TvCid(cid, name, name, img=img)
                    result.append(program)
                except Exception, e:
                    self.log('getChannelList exception while looping: %s' % getExceptionString())

            if len(result) <= 0:
                self.log('Error while parsing service %s, returned data is: %s' % (self.serviceName, httpdata))
                xbmcgui.Dialog().notification(strings(SERVICE_ERROR), strings(SERVICE_NO_PREMIUM) + ' ' + self.serviceName, time=15000, sound=False)

            self.printedError = False

        except Exception, e:
            self.log('getChannelList exception: %s' % getExceptionString())
        return result

    def getChannelStream(self, chann):
        try:
            videoUrl = self.getVideoUrl(chann.cid)
            if videoUrl is None and self.gotPremium:
                self.log('Attempting to log in one more time since first one failed! Session ended?')
                if self.loginService():
                    videoUrl = self.getVideoUrl(chann.cid)

            if videoUrl:
                chann.strm = videoUrl
                self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (chann.cid, chann.name, chann.strm))
                return chann

        except Exception, e:
            self.log('getChannelStream exception while looping: %s' % getExceptionString())
        return None

    def getVideoUrl(self, cid):
        try:
            url = self.url + 'watch.php?id=%s' % cid
            self.sl.getJsonFromExtendedAPI(url, cookieFile = COOKIE_FILE, load_cookie = True)
            headers = { 'User-Agent' : HOST, 'Referer' : url }
            url2 = self.url + 'porter.php?ch=%s' % cid
            data = self.sl.getJsonFromExtendedAPI(url2, customHeaders=headers, cookieFile = COOKIE_FILE, load_cookie = True)
            if not data or ('Brak wolnych miejsc!' in data and self.useFreeAccount == 'true'):
                if not self.printedError:
                    xbmcgui.Dialog().notification(strings(SERVICE_ERROR), strings(69037) + self.serviceName, time=10000, sound=False)
                    self.printedError = True
                self.log('Brak wolnych miejsc w wizja.tv')
                return None

            if 'killme.php' in data:
                # Need to release stream
                self.log('killme.php visible in data - killing old streams!')
                self.sl.getJsonFromExtendedAPI(self.url + 'killme.php?id=%s' % cid, cookieFile = COOKIE_FILE, load_cookie = True)
                data = self.sl.getJsonFromExtendedAPI(url2, customHeaders=headers, cookieFile = COOKIE_FILE, load_cookie = True)

            if 'adki, lub zaloguj si' in data:
                self.log('getChannel detected no premium open stream - trying to kill it')
                xbmc.Player().stop()
                self.sl.getJsonFromExtendedAPI(self.url + 'killme.php?id=%s' % cid, cookieFile = COOKIE_FILE, load_cookie = True)
                data = self.sl.getJsonFromExtendedAPI(url2, customHeaders=headers, cookieFile = COOKIE_FILE, load_cookie = True)

            link = re.compile('src: "(.*?)"').findall(data)
            if len(link) > 0:
                tmpRTMP = urllib.unquote(link[0]).decode('utf8')
                tmpRTMP = re.compile('rtmp://(.*?)/(.*?)/(.*?)\?(.*?)\&streamType').findall(tmpRTMP)
                #rtmp = 'rtmp://' + tmpRTMP[0][0] + '/' + tmpRTMP[0][1] + '?' + tmpRTMP[0][3] + ' playpath=' + tmpRTMP[0][2] + '?' + tmpRTMP[0][3] + ' app=' + tmpRTMP[0][1] + '?' +tmpRTMP[0][3] + ' swfVfy=1 flashver=WIN\\2020,0,0,306 timeout=25 swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v3.swf live=true pageUrl='+url
                rtmp = 'rtmp://' + tmpRTMP[0][0] + '/' + tmpRTMP[0][1] + '?' + tmpRTMP[0][3] + ' app=' + tmpRTMP[0][1] + '?' + tmpRTMP[0][3] + ' playpath=' + tmpRTMP[0][2] + '?' +tmpRTMP[0][3] + ' swfVfy=1 flashver=LNX\\25,0,0,12 timeout=25 swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v4.swf live=true pageUrl=' + url
                return rtmp
            else:
                self.log('getVideoUrl error could not find video URL in data: %s' % str(data))

            return None

        except Exception, e:
            self.log('getVideoUrl exception: %s' % getExceptionString())
        return None
