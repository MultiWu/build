#      Copyright (C) 2016 Andrzej Mleczko

import os, re, copy
import xbmc, xbmcgui
import urlparse
from strings import *
from serviceLib import *

serviceName         = 'YoyTV'
yoyUrl              = 'http://yoy.tv/'
COOKIE_FILE         = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('profile')) , 'yoytv.cookie')

class YoyTVUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'yoytvmap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('yoytv_enabled')
        self.login              = ADDON.getSetting('yoytv_username').strip()
        self.password           = ADDON.getSetting('yoytv_password').strip()
        self.servicePriority    = int(ADDON.getSetting('priority_yoytv'))
        self.url                = yoyUrl
        self.nrOfPagesToParse   = 10
        self.shownLoginError    = False

    def downloadThread(self, url, threadData):
        data = self.sl.getJsonFromExtendedAPI(url, cookieFile = COOKIE_FILE, load_cookie = True)
        if data is not None:
            threadData.append(data)

    def loginService(self):
        data = self.sl.getJsonFromExtendedAPI(self.url + 'signin', cookieFile = COOKIE_FILE, save_cookie = True)
        if not data or len(self.login) <= 0:
            self.loginErrorMessage()
            return False

        post = {}
        post['remember_me']='1'
        post['email'] = self.login
        post['password'] = self.password
        post['_token'] = self.sl.parseDOM(data, 'input', ret='value', attrs={'name' : '_token'})[0]
        data = self.sl.getJsonFromExtendedAPI(self.url + 'signin', post_data = post, cookieFile = COOKIE_FILE, load_cookie = True, save_cookie = True, max_conn_time=7)
        if data is None or 'http://yoy.tv/signout' not in data:
            if not self.shownLoginError:
                self.loginErrorMessage()
                self.shownLoginError = True
                return False

        return True

    def getChannelList(self, silent):
        result = list()
        regexReplaceList = list()

        regexReplaceList.append( re.compile('[^A-Za-z0-9/:]+',          re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)PL(\s|$)',           re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)Polska(\s|$)',       re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)Poland(\s|$)',       re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)Europe(\s|$)',       re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)SD(\s|$)',           re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)ADULT:',             re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)PL:',                re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)PORNO(\s|$)',        re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s|^)EROTIC(\s|$)',       re.IGNORECASE) )
        regexReplaceList.append( re.compile('(\s+)',                    re.IGNORECASE) )

        self.log('\n\n')
        self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
        self.log('[UPD] -------------------------------------------------------------------------------------')
        self.log('[UPD] %-10s %-35s %-35s' % ( '-CID-', '-NAME-', '-IMG-'))

        try:
            if not self.loginService():
                return result

            #Try to check how mange pages should we parse
            try:
                data = self.sl.getJsonFromExtendedAPI(self.url + 'channels?live=1&country=140', cookieFile = COOKIE_FILE, load_cookie = True)
                pagesRe = re.compile('.*?country=140&page=(\d*).*?')
                pages = pagesRe.findall(data)
                pages = [ int(x) for x in pages ]
                maxPages = int(max(pages)) + 1
                if maxPages > self.nrOfPagesToParse:
                    self.nrOfPagesToParse = maxPages
            except:
                self.log('getChannelList get number of pages exception: %s' % getExceptionString())

            threadList = list()
            threadData = list()
            for page in range(1, self.nrOfPagesToParse):
                thread = threading.Thread(name='downloadThread', target = self.downloadThread, args=[self.url + 'channels?live=1&country=140&page=%s' % page, threadData])
                threadList.append(thread)
                thread.start()

            #thread = threading.Thread(name='downloadThread', target = self.downloadThread, args=[self.url + 'channels?category=erotyka', threadData])
            #threadList.append(thread)
            #thread.start()

            for thread in threadList:
                while thread.is_alive():
                    xbmc.sleep(300)

            del threadList[:]

            for data in threadData:
                if data is not None:
                    data = self.sl.parseDOM(data, 'a', attrs={'class' : 'thumb-info team'})
                    parsedData = list()
                    for i in data:
                        try:
                            row = i.replace('>>', '')
                            img  = self.sl.parseDOM(row, 'img', ret='src')[0]
                            name = self.sl.parseDOM(row, 'img', ret='alt')[0]
                            parsedData.append([img, name])
                        except Exception, e:
                            self.log('getChannelList exception: %s, while parsing data: %s' % (getExceptionString(), row) )

                    for item in parsedData:
                        cid = item[0].replace('http://yoy.tv/channel/covers/','').replace('.jpg?cache=32','').replace('.jpg','').encode('utf-8').strip()
                        name = item[1].upper().encode('utf-8').strip()
                        img = item[0].replace('?cache=32', '').encode('utf-8').strip()

                        for regexReplace in regexReplaceList:
                            name = regexReplace.sub(' ', name)

                        name = name.replace('  ', ' ').strip()

                        self.log('[UPD] %-10s %-35s %-35s' % (cid, name, img))
                        program = TvCid(cid, name, name, img=img)
                        result.append(program)

                    del parsedData[:]

            del threadData[:]

        except Exception, e:
            self.log('getChannelList exception: %s' % getExceptionString())
        return result

    def getChannelStream(self, chann):
        try:
            url = self.url + 'channels/%s' % chann.cid
            data = self.sl.getJsonFromExtendedAPI(url + '?tran=r', cookieFile = COOKIE_FILE, load_cookie = True)

            if not data or '<title>Kup konto premium w portalu yoy.tv</title>' in data:
                self.log('NO PREMIUM, DATA: %s' % str(data))
                if not self.shownLoginError:
                    self.noPremiumMessage()
                    self.shownLoginError = True
                return None

            try:
                myobj = self.sl.parseDOM(data, 'form', ret='action')
                if len(myobj) > 0:
                    for tekst in myobj:
                        if 'yoy.tv/accept' in tekst:
                            post = {}
                            post['_token'] = self.sl.parseDOM(data, 'input', ret='value', attrs={'name': '_token'})[0]
                            data = self.sl.getJsonFromExtendedAPI(tekst, post_data = post, cookieFile = COOKIE_FILE, load_cookie = True)
            except Exception, e:
                self.log('getChannelStream exception while trying to find accept form: %s' % (getExceptionString(), str(data)))

            m3u = re.compile('"(http.*?.m3u8)"').findall(data)
            if m3u:
                myurl = m3u[0]
            else:
                myobj = self.sl.parseDOM(data, 'object', ret='data', attrs={'type': 'application/x-shockwave-flash'})[0].encode('utf-8')
                data = self.sl.parseDOM(data, 'param', ret='value', attrs={'name' : 'FlashVars'})[0].encode('utf-8')

                # Decoded by MrKnow - thanks!

                p = urlparse.parse_qs(data)
                myurl = p['fms'][0] + '/' + p['cid'][0] + ' swfUrl=' + myobj + ' swfVfy=true tcUrl=' + p['fms'][0] + '/_definst_ live=true timeout=15 pageUrl=' + url
                myurl = p['fms'][0] + '/' + p['cid'][0] + ' swfUrl=' + myobj + ' swfVfy=true live=true timeout=15 pageUrl=' + url

            chann.strm = myurl
            self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (str(chann.cid), str(chann.name), str(chann.strm)) )
            return chann

        except Exception, e:
            self.log('getChannelStream exception while looping: %s' % getExceptionString())
        return None
