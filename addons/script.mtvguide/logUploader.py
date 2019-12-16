#      Copyright (C) 2016 Andrzej Mleczko

import os, urllib, urllib2, httplib, datetime
import xbmc, xbmcgui
from strings import *

URL      = 'https://paste.ubuntu.com/'
LOGPATH  = xbmc.translatePath('special://logpath')
LOGFILE  = os.path.join(LOGPATH, 'kodi.log')
LOGFILE2 = os.path.join(LOGPATH, 'spmc.log')
LOGFILE3 = os.path.join(LOGPATH, 'xbmc.log')

class LogUploader:
    def __init__(self):
        if os.path.isfile(LOGFILE):
            logContent = self.getLog(LOGFILE)
        elif os.path.isfile(LOGFILE2):
            logContent = self.getLog(LOGFILE2)
        elif os.path.isfile(LOGFILE3):
            logContent = self.getLog(LOGFILE3)
        else:
            xbmcgui.Dialog().ok(strings(30150).encode('utf-8'),"\n" + "Unable to find kodi log file")
            return

        logUrl = self.upload(logContent)
        if logUrl:
            xbmcgui.Dialog().ok(strings(31004).encode('utf-8'),"\n" + strings(69033).encode('utf-8') + logUrl)
        else:
            xbmcgui.Dialog().ok(strings(30150).encode('utf-8'),"\n" + strings(69034).encode('utf-8'))

    def getLog(self, filename):
        if os.path.isfile(filename):
            content = None
            with open(filename, 'r') as content_file:
                content = content_file.read()
            if content is None:
                deb('LogUploader upload ERROR could not get content of log file')
            return content
        return None

    def upload(self, data):
        if data is None:
            return None
        params = {}
        params['poster'] = 'anonymous'
        params['content'] = data[-1500000:]
        params['syntax'] = 'text'
        params['expiration'] = 'week'
        params = urllib.urlencode(params)
        startTime = datetime.datetime.now()

        try:
            page = urllib2.urlopen(URL, params, timeout=10)
        except Exception, ex:
            deb('LogUploader upload failed to connect to the server, exception: %s' % getExceptionString())
            deb('LogUploader Uploading files took: %s' % (datetime.datetime.now() - startTime).seconds)
            return None

        deb('LogUploader Uploading files took: %s' % (datetime.datetime.now() - startTime).seconds)

        try:
            page_url = page.url.strip()
            deb('LogUploader success: %s' % str(page_url))
            return page_url
        except Exception, ex:
            deb('LogUploader unable to retrieve the paste url, exception: %s' % getExceptionString())

        return None

logup = LogUploader()
