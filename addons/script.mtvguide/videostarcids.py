#      Copyright (C) 2019 Mariusz Brychcy
#      Copyright (C) 2019 Andrzej Mleczko

import os, copy
import xbmc
from strings import *
from serviceLib import *
from random import randrange
import requests
import json

serviceName         = 'WP Pilot'
videostarUrl        = 'https://pilot.wp.pl/api/'
COOKIE_FILE         = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('profile')) , 'videostar.cookie')
headers = {
    'user-agent': 'ExoMedia 4.3.0 (43000) / Android 8.0.0 / MIBOX3',
    'accept': 'application/json',
    'x-version': 'pl.videostar|3.25.0|Android|26|MIBOX3',
    'content-type': 'application/json; charset=UTF-8'
}

login_url = 'https://pilot.wp.pl/api/v1/user_auth/login'

dataPath = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')
cacheFile = os.path.join(dataPath, 'cache.db')

sess = requests.Session()

class VideoStarUpdater(baseServiceUpdater):
    def __init__(self):
        self.serviceName        = serviceName
        self.localMapFile       = 'videostarmap.xml'
        baseServiceUpdater.__init__(self)
        self.serviceEnabled     = ADDON.getSetting('videostar_enabled')
        self.login              = ADDON.getSetting('videostar_username').strip()
        self.password           = ADDON.getSetting('videostar_password').strip()
        self.servicePriority    = int(ADDON.getSetting('priority_videostar'))
        self.url                = videostarUrl
        self.addDuplicatesToList = True


    
    def loginService(self):
        try:
            if len(self.password) > 0 and len(self.login) > 0:
                data = {'device': 'android', 'login': self.login, 'password': self.password}

                response = requests.post(
                    login_url,
                    json=data,
                    verify=False,
                    headers=headers
                )

                meta = response.json().get('_meta', None)
                if meta is not None:
                    if meta.get('error', {}).get('name', None) is not None:
                        self.log('Exception while trying to log in: %s' % getExceptionString())
                        self.loginErrorMessage()
                    return False

                self.saveToDB('wppilot_cache', self.cookiesToString(response.cookies))
                return True

        except:
            self.log('Exception while trying to log in: %s' % getExceptionString())
            self.loginErrorMessage()
        return False

    def saveToDB(self, table_name, value):
        import sqlite3
        import os
        if os.path.exists(cacheFile):
            os.remove(cacheFile)
        else:
            print('File does not exists')
        conn = sqlite3.connect(cacheFile, detect_types=sqlite3.PARSE_DECLTYPES,
                               cached_statements=20000)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS Cache(%s TEXT)' % table_name)
        c.execute("INSERT INTO Cache('%s') VALUES ('%s')" % (table_name, value))
        conn.commit()
        c.close()

    def readFromDB(self):
        import sqlite3
        conn = sqlite3.connect(cacheFile, detect_types=sqlite3.PARSE_DECLTYPES,
                               cached_statements=20000)
        c = conn.cursor()
        c.execute("SELECT * FROM Cache")
        for row in c:
            if row:
                c.close()
                return row[0]

    def cookiesToString(self, cookies):
        try:
            return "; ".join([str(x) + "=" + str(y) for x, y in cookies.get_dict().items()])
        except Exception as e:
            print (e)
            return ''

    def getChannelList(self, silent):
        result = list()
        if not self.loginService():
            return result

        self.log('\n\n')
        self.log('[UPD] Pobieram liste dostepnych kanalow %s z %s' % (self.serviceName, self.url))
        self.log('[UPD] -------------------------------------------------------------------------------------')
        self.log('[UPD] %-10s %-35s %-15s %-20s %-35s' % ( '-CID-', '-NAME-', '-GEOBLOCK-', '-ACCESS STATUS-', '-IMG-'))

        try:
            cookies = self.readFromDB()
            headers.update({'Cookie': cookies})
            httpdata = requests.get(self.url + '/channels/list/android-plus', verify=False, headers=headers).json()
            #httpdata = self.sl.getJsonFromExtendedAPI(self.url + '/channels/list/android-plus', cookieFile = COOKIE_FILE, load_cookie = True, jsonLoadsResult=True, skipSslCertificate=True, customHeaders=headers)
            if httpdata is None or httpdata['status'] != 'ok':
                self.log('Error while trying to get channel list, result: %s' % str(httpdata))
                self.noPremiumMessage()
                return result

            channels = httpdata['channels']
            for channel in channels:
                #self.log('Channel %s' % channel)
                name = channel['name']
                cid  = channel['id']
                img  = channel['thumbnail']
                geoblocked = channel['geoblocked']
                access = channel['access_status']
                self.log('[UPD] %-10s %-35s %-15s %-20s %-35s' % (cid, name, geoblocked, access, img))
                if geoblocked != True and access != 'unsubscribed':
                    program = TvCid(cid, name, name, img=img)
                    result.append(program)

            if len(result) <= 0:
                self.log('Error while parsing service %s, returned data is: %s' % (self.serviceName, str(httpdata)))
                self.noPremiumMessage()

        except:
            self.log('getChannelList exception: %s' % getExceptionString())
        return result

    def getChannelStream(self, chann):
        data = None
        try:
            cookies = self.readFromDB()
            url = self.url + 'v1/channel/%s' % chann.cid
            data = {'format_id': '2', 'device': 'm_web'}

            headers.update({'Cookie': cookies})
            response = requests.get(url, params=data, verify=False, headers=headers).json()

            if 'hls' in response[u'data'][u'stream_channel'][u'streams'][0][u'type']:
                data = response[u'data'][u'stream_channel'][u'streams'][0][u'url'][0] + '|user-agent=' + headers['user-agent']

            elif data is None: # or data['status'] != 'ok'
                self.log('Error getting channel stream, result: %s' % str(data))
                return None

            else:
                data = response[u'data'][u'stream_channel'][u'streams'][1][u'url'][0] + '|user-agent=' + headers['user-agent']


            if data is not None and data != "":
                chann.strm = data
                self.log('getChannelStream found matching channel: cid: %s, name: %s, rtmp: %s' % (chann.cid, chann.name, chann.strm))
                return chann
            else:
                self.log('getChannelStream error getting channel stream2, result: %s' % str(data))
                return None
        except Exception, e:
            self.log('getChannelStream exception while looping: %s\n Data: %s' % (getExceptionString(), str(data)))
        return None
