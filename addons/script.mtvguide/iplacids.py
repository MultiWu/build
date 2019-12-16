#      Copyright (C) 2016 Andrzej Mleczko

# Most of IPLA implementation is taken from MrKnow - thank you very much MrKnow!

import re, copy, random, json
from strings import *
from serviceLib import *

serviceName         = 'Ipla'
iplaUrl             = 'http://www.ipla.tv/'

headers     = {'User-Agent':'mipla_ios/122','Content-Type':'application/x-www-form-urlencoded', 'Accept-Language': 'pl-pl'}
headers1    = {'User-Agent':'mipla_ios/122', 'Accept-Language':'pl-pl'}
headers2    = {'User-Agent':'ipla_MOBILE/122.0 (iPhone; ARM OS 10_0_2 like Mac OS X)'}
headers3    = {'User-Agent':'IPLA/4.2.2.5 CFNetwork/808.0.2 Darwin/16.0.0'}

url_system      = 'https://gm2.redefine.pl/rpc/system/'
url_preauth     = 'http://b2c.redefine.pl/rpc/auth/'
url_category    = 'http://b2c.redefine.pl/rpc/navigation/'
url_navigation  = 'http://b2c.redefine.pl/rpc/navigation/'
url_hls         = 'http://hls.redefine.pl'
post_init       = json.loads('{"jsonrpc":"2.0","method":"getConfiguration","id":2,"params":{"message":{"id":"CC3DFE81-1C70-403A-9C52-FC10EC51125A","timestamp":"2017-05-16T00:08:57Z"}}}')
post_preauth    = json.loads('{"jsonrpc":"2.0","method":"getAllRules","id":3,"params":{"rulesType":"login","message":{"id":"CCE2DB52-E7F7-4B3B-88F4-8FD4D919E4DF","timestamp":"2017-05-15T23:02:20Z"}}}')


class IplaUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'iplamap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('ipla_enabled')
        self.login              = ADDON.getSetting('ipla_username').strip()
        self.password           = ADDON.getSetting('ipla_password').strip()
        self.servicePriority    = int(ADDON.getSetting('priority_ipla'))
        self.url                = iplaUrl
        self.addDuplicatesToList = True
        self.loginData = None
        self.ipla_passwdmd5 = None

    def getSystemId(self):
        def gen_hex_code(myrange=6):
            return ''.join([random.choice('0123456789ABCDEF') for x in range(myrange)])

        systemid = ADDON.getSetting('ipla.systemid').strip()
        if (systemid == ''):
            myrand = gen_hex_code(10) + '-' + gen_hex_code(4) + '-' + gen_hex_code(4) + '-' + gen_hex_code(4) + '-' + gen_hex_code(12)
            myrand = myrand.strip()
            ADDON.setSetting(id='ipla.systemid', value=str(myrand))
            self.log('generated systemID: %s' % myrand)
        return systemid

    def loginService(self):
        url_auth = 'https://getmedia.redefine.pl/tv/menu.json?passwdmd5=' + self.password + '&api_client=mipla_ios&login=' + self.login + '&machine_id=iOS%' + self.getSystemId() + '&outformat=2&api_build=122'
        result = self.sl.getJsonFromExtendedAPI(url_system, post_data=post_init, customHeaders=headers, json_dumps_post=True)
        result = self.sl.getJsonFromExtendedAPI(url_preauth, post_data=post_preauth, customHeaders=headers, json_dumps_post=True)
        result = self.sl.getJsonFromExtendedAPI(url_auth, customHeaders=headers1, jsonLoadsResult=True)
        if len(self.login) <= 0 or result is None or result['config']['auth_errors']['auth'] != 200:
            self.log('Login error, returned data is %s' % str(result))
            self.loginErrorMessage()
            return False

        self.log('Logged in, data: %s' % str(result))
        self.loginData = result
        return True

    def getChannelList(self, silent):
        result = list()
        if not self.loginService():
            return result

        self.log('\n\n')
        self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
        self.log('[UPD] -------------------------------------------------------------------------------------')
        self.log('[UPD] %-10s %-35s %-35s' % ( '-CID-', '-NAME-', '-IMG-'))

        try:
            myperms = []
            items = []
            for i in self.loginData['config']['access_groups']:
                if 'sc:' in i['code']:
                    myperms.append(str(i['code']))
                if 'oth:' in i['code']:
                    myperms.append(str(i['code']))

            try:
                self.ipla_passwdmd5 = self.loginData['config']['user']['passwdmd5']

                my_action1 = self.loginData['config']['traffic_url'] + 'id=' + self.loginData['config']['traffic_id'] + '&extra=GoalName%3DInterfejs/Login/Email%7Cc%3Dipla-ios/122/10.0.2/Apple/iPhone&et=action'
                my_action2 = self.loginData['config']['traffic_url'] + 'id=' + self.loginData['config']['traffic_id'] + '&extra=GoalName%3DIInterfejs/Start_Aplikacji/Kolejny%7Cc%3Dipla-ios/122/10.0.2/Apple/iPhone&et=action'
                my_action3 = self.loginData['config']['traffic_url'] + 'id=' + self.loginData['config']['traffic_id'] + '&extra=GoalName%3DInterfejs/Przegl%C4%85danie%7Cc%3Dipla-ios/122/10.0.2/Apple/iPhone&et=view'

                self.sl.getJsonFromExtendedAPI(my_action1, customHeaders=headers2)
                self.sl.getJsonFromExtendedAPI(my_action2, customHeaders=headers2)
                self.sl.getJsonFromExtendedAPI(my_action3, customHeaders=headers2)
            except Exception, e:
                self.log('getChannelList exception when extracting login data, except: %s' % getExceptionString())
                return result

            post_getCat         = json.loads('{"jsonrpc":"2.0","method":"getCategoryWithFlatNavigation","id":4,"params":{"catid":0,"authData":{"login":"' + self.login + '"},"message":{"id":"47B80EF0-19D0-4BD0-82FF-80BC50EDF2A9","timestamp":"2017-05-15T23:02:22Z"}}}')
            post_getTVChannels  = json.loads('{"jsonrpc":"2.0","method":"getTvChannels","id":5,"params":{"authData":{"login":"' + self.login + '"},"message":{"id":"4B737B56-A11D-4E65-BC86-47EA1E40EC4D","timestamp":"2017-05-15T17:03:21Z"}}}')

            data = self.sl.getJsonFromExtendedAPI(url_navigation, post_data=post_getTVChannels, customHeaders=headers, json_dumps_post=True, jsonLoadsResult=True)

            if data is None:
                self.log('getChannelList url_navigation return empty data!')
                return result

            for i in data['result']['results']:
                item = {}
                channelperms = i['grantExpression'].split('*')
                channelperms = [w.replace('+plat:all', '') for w in channelperms]
                for j in myperms:
                    if j in channelperms:
                        item['img'] = i['thumbnails'][-1]['src'].encode('utf-8')
                        item['id'] = i['id']
                        item['title'] = i['title'].upper().encode('utf-8')
                        item['plot'] = i['description'].encode('utf-8')
                        item = {'title': item['title'], 'originaltitle': item['title'], 'genre': '0', 'plot': item['plot'], 'name':item['title'], 'tagline': '0',  'poster': item['img'], 'fanart': '0', 'id':item['id'], 'service':'ipla', 'next': ''}
                        items.append(item)

            dupes = []
            filter = []
            for entry in items:
                if not entry['id'] in dupes:
                    filter.append(entry)
                    dupes.append(entry['id'])

            items = filter
            #self.log('Channels %s' % str(items))

            sdRegex = re.compile(' SD(\s|$)',   re.IGNORECASE)
            plRegex = re.compile(' PL(\s|$)',   re.IGNORECASE)

            for item in items:
                try:
                    cid     = item['id']
                    name    = item['name']
                    img     = item['poster']

                    name    = sdRegex.sub(' ', name).replace('  ', ' ').strip()
                    name    = plRegex.sub(' ', name).replace('  ', ' ').strip()

                    self.log('[UPD] %-10s %-35s %-35s' % (cid, name, img))
                    program = TvCid(cid, name, name, img=img)
                    result.append(program)
                except Exception, e:
                    self.log('getChannelList exception while adding channels to list: %s, channel: %s, fullList: %s' % (getExceptionString(), str(item), str(items)))

            if len(result) <= 0:
                self.log('Error while parsing service %s, returned data is: %s' % (self.serviceName, httpdata))

        except Exception, e:
            self.log('getChannelList exception: %s' % getExceptionString())
        return result

    def getChannelStream(self, chann):
        try:
            post_getMedia = json.loads('{"jsonrpc":"2.0","method":"getMedia","id":10,"params":{"cpid":0,"message":{"id":"F26642A8-8000-4C7A-B1CB-C2EADFD82E23","timestamp":"2017-05-16T00:53:25Z"},"authData":{"login":"' + self.login + '"},"mediaId":"' + str(chann.cid) + '"}}')
            post_perPlayData = json.loads('{"jsonrpc":"2.0","method":"prePlayData","id":"-1864568404","params":{"mediaId":"' + str(chann.cid) + '","cpid":0,"authData":{"login":"' + self.login + '"}}}')

            result = self.sl.getJsonFromExtendedAPI(url_navigation, post_data=post_getMedia, customHeaders=headers, json_dumps_post=True)
            result = self.sl.getJsonFromExtendedAPI(url_navigation, post_data=post_perPlayData, customHeaders=headers, json_dumps_post=True, jsonLoadsResult=True)

            try:
                url = None
                for mediaSource in reversed(result['result']['mediaItem']['playback']['mediaSources']):
                    if mediaSource['authorizationServices'] is not None and bool(mediaSource['authorizationServices']):
                        url = mediaSource['authorizationServices']['pseudo']['url']
                        break
                if not url:
                    self.log('getChannelStream ERROR - did not find proper url is authorizationServices!')
                myid = result['result']['mediaItem']['playback']['mediaId']['id']
            except Exception, e:
                self.log('getChannelStream exception when extracting result: %s, result: %s' % (getExceptionString(), str(result)))
                return None

            url = url + '?cltype=mobile&cpid=0&id=' + myid + '&login=' + self.login + '&passwdmd5=' + self.ipla_passwdmd5 + '&client_id=iOS%' + self.getSystemId() + '&outformat=2'
            result = self.sl.getJsonFromExtendedAPI(url, customHeaders=headers1, jsonLoadsResult=True)

            try:
                url = result['resp']['license']['url'] + '|User-Agent='+urllib.quote_plus('IPLA/4.2.2.5 CFNetwork/808.0.2 Darwin/16.0.0')
                url = result['resp']['license']['url']
            except Exception, e:
                self.log('getChannelStream exception when extracting url from result: %s, result: %s' % (getExceptionString(), str(result)))
                return None

            result = self.sl.getJsonFromExtendedAPI(url, customHeaders=headers3)

            try:
                link = re.findall("BANDWIDTH=\d+\n(.*?m3u8)", result.decode('utf-8'), re.MULTILINE)[0]
            except Exception, e:
                self.log('getChannelStream exception when extracting BANDWIDTH from result: %s, result: %s' % (getExceptionString(), str(result)))
                return None

            if url_hls in link:
                url = link + '?userid=iOS%' + self.getSystemId() + '&initial|User-Agent=' + urllib.quote_plus(headers2['User-Agent'])
            else:
                url = url_hls + link + '?userid=iOS%' + self.getSystemId() + '&initial|User-Agent='+ urllib.quote_plus(headers2['User-Agent'])

            if url is not None and url != "":
                chann.strm = url
                self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (chann.cid, chann.name, chann.strm))
                return chann
            else:
                self.log('getChannelStream url is empty, url: %s' % str(url))
                return None

        except Exception, e:
            self.log('getChannelStream exception while looping: %s' % getExceptionString())
        return None
