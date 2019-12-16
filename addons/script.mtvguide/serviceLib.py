#      Copyright (C) 2016 Andrzej Mleczko
#      Copyright (C) 2018 Mariusz Brychcy

import os, sys, urllib, urllib2, httplib, urlparse, StringIO, cookielib, re, socket, copy, threading
import time, datetime
import xbmc, xbmcgui
from xml.etree import ElementTree
from strings import *
import simplejson as json
import strings as strings2
import zlib
try:
    import ssl
except:
    pass

HOST        = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
pathAddons  = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'addons.ini')
pathMapBase = os.path.join(ADDON.getAddonInfo('path'), 'resources')
onlineMapPathBase = M_TVGUIDE_SUPPORT + 'maps/'

try:
    MAX_CONNECTION_TIME = int(ADDON.getSetting('max_connection_time'))
except:
    MAX_CONNECTION_TIME = 30

HTTP_ConnectionTimeout = 10

class ShowList:
    def __init__(self, logCall=deb):
        self.logCall = logCall

    def decode(self, string):
        json_ustr = json.dumps(string, ensure_ascii=False)
        return json_ustr.encode('utf-8')

    def JsonToSortedTab(self, json):
        strTab = []
        outTab = []
        for v,k in json.iteritems():
            strTab.append(int(v))
            strTab.append(k)
            outTab.append(strTab)
            strTab = []
        outTab.sort(key=lambda x: x[0])
        return outTab

    def getJsonFromAPI(self, url, post={}):
        result_json = None
        raw_json = None
        try:
            data     = urllib.urlencode(post)
            reqUrl   = urllib2.Request(url, data)
            reqUrl.add_header('User-Agent', 'Python-urllib/2.1')
            reqUrl.add_header('Keep-Alive', 'timeout=60')
            reqUrl.add_header('Connection', 'Keep-Alive')
            reqUrl.add_header('ContentType', 'application/x-www-form-urlencoded')
            reqUrl.add_header('Accept-Encoding', 'gzip')

            startTime = datetime.datetime.now()
            while (datetime.datetime.now() - startTime).seconds < MAX_CONNECTION_TIME and strings2.M_TVGUIDE_CLOSING == False:
                try:
                    raw_json = urllib2.urlopen(reqUrl, timeout = HTTP_ConnectionTimeout)
                    content_json = raw_json.read()
                    if raw_json.headers.get("Content-Encoding", "") == "gzip":
                        content_json = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(content_json)

                    result_json = json.loads(content_json)
                    raw_json.close()
                    break
                except (httplib.IncompleteRead, socket.timeout) as ex:
                    self.logCall('ShowList getJsonFromAPI exception: %s - retrying seconds = %s' % (str(ex), (datetime.datetime.now() - startTime).seconds))

                except urllib2.HTTPError as ex:
                    if ex.code in [500, 408]:
                        self.logCall('ShowList getJsonFromAPI exception: %s - retrying seconds = %s' % (str(ex), (datetime.datetime.now() - startTime).seconds))
                    else:
                        raise

                except urllib2.URLError as ex:
                    if 'timed out' in str(ex) or 'Timeout' in str(ex):
                        self.logCall('ShowList getJsonFromAPI exception: %s - retrying seconds = %s' % (str(ex), (datetime.datetime.now() - startTime).seconds))
                    else:
                        raise

                try:
                    if raw_json:
                        raw_json.close()
                        raw_json = None
                except:
                    pass
                if strings2.M_TVGUIDE_CLOSING:
                    self.logCall('ShowList getJsonFromAPI M_TVGUIDE_CLOSING - aborting!')
                    break
                xbmc.sleep(150)

        except (urllib2.URLError, NameError, ValueError, httplib.BadStatusLine) as ex:
            self.logCall('ShowList getJsonFromAPI exception: %s - aborting!' % str(ex))
            return None
        return result_json

    def getJsonFromExtendedAPI(self, url, post_data = None, save_cookie = False, load_cookie = False, cookieFile = None, jsonLoadsResult = False, jsonLoadResult = False, customHeaders = None, max_conn_time = MAX_CONNECTION_TIME, getResponseUrl=False, skipSslCertificate=False, json_dumps_post=False, http_timeout=HTTP_ConnectionTimeout, verbose=True):
        result_json = None
        raw_json = None
        customOpeners = []
        cj = cookielib.LWPCookieJar()
        url = url.replace(' ','%20')

        def urlOpen(req, customOpeners):
            if skipSslCertificate and sys.version_info >= (2, 7, 9):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                customOpeners += [urllib2.HTTPSHandler(context=ctx)]

            if len(customOpeners) > 0:
                opener = urllib2.build_opener( *customOpeners )
                response = opener.open(req, timeout = http_timeout)
            else:
                response = urllib2.urlopen(req, timeout = http_timeout)
            return response

        try:
            if cookieFile is not None:
                customOpeners.append( urllib2.HTTPCookieProcessor(cj) )
                if load_cookie == True and cookieFile is not None and os.path.isfile(cookieFile):
                    cj.load(cookieFile, ignore_discard = True)

            if customHeaders is not None:
                headers = customHeaders
            else:
                headers = { 'User-Agent' : HOST }
                headers['Keep-Alive'] = 'timeout=60'
                headers['Connection'] = 'Keep-Alive'
                headers['ContentType'] = 'application/x-www-form-urlencoded'
                headers['Accept-Encoding'] = 'gzip'

            if json_dumps_post:
                data = json.dumps(post_data)
            elif post_data:
                data = urllib.urlencode(post_data)
            else:
                data = None
            reqUrl = urllib2.Request(url=url, data=data, headers=headers)

            startTime = datetime.datetime.now()
            while (datetime.datetime.now() - startTime).seconds < max_conn_time and strings2.M_TVGUIDE_CLOSING == False:
                try:
                    raw_json = urlOpen(reqUrl, customOpeners)
                    if getResponseUrl:
                        result = raw_json.geturl()
                        raw_json.close()
                        return result
                    result_json = raw_json.read()
                    if raw_json.headers.get("Content-Encoding", "") == "gzip":
                        result_json = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(result_json)

                    if jsonLoadsResult == True:
                        result_json = json.loads(result_json)
                    raw_json.close()
                    break
                except (httplib.IncompleteRead, socket.timeout) as ex:
                    if verbose:
                        self.logCall('ShowList getJsonFromExtendedAPI exception: %s, url: %s - retrying seconds = %s' % (str(ex), url, (datetime.datetime.now() - startTime).seconds))

                except urllib2.HTTPError as ex:
                    if ex.code in [500, 408]:
                        if verbose:
                            self.logCall('ShowList getJsonFromExtendedAPI exception: %s, url: %s - retrying seconds = %s' % (str(ex), url, (datetime.datetime.now() - startTime).seconds))
                    else:
                        raise

                except urllib2.URLError as ex:
                    if 'timed out' in str(ex) or 'Timeout' in str(ex):
                        if verbose:
                            self.logCall('ShowList getJsonFromExtendedAPI exception: %s, url: %s - retrying seconds = %s' % (str(ex), url, (datetime.datetime.now() - startTime).seconds))
                    else:
                        raise

                try:
                    if raw_json:
                        raw_json.close()
                        raw_json = None
                except:
                    pass
                if strings2.M_TVGUIDE_CLOSING:
                    self.logCall('ShowList getJsonFromExtendedAPI M_TVGUIDE_CLOSING - aborting!')
                    break
                xbmc.sleep(150)

            if cookieFile is not None and save_cookie == True:
                cj.save(cookieFile, ignore_discard = True)

        except (urllib2.URLError, NameError, ValueError, httplib.BadStatusLine) as ex:
            if verbose:
                self.logCall('ShowList getJsonFromExtendedAPI exception: %s - aborting!' % str(ex))
            return None

        return result_json

    def getCookieItem(self, cookiefile, item = None):
        ret = ''
        if os.path.isfile(cookiefile):
            cj = cookielib.LWPCookieJar()
            cj.load(cookiefile, ignore_discard = True)
            for cookie in cj:
                if not item:
                    ret += '%s=%s;' % (cookie.name, cookie.value)
                elif cookie.name == item:
                    ret = cookie.value
        return ret

    def downloadUrl(self, url, retryFailed = True):
        fileContent = None
        try:
            reqUrl   = urllib2.Request(url)
            reqUrl.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20121213 Firefox/19.0')
            reqUrl.add_header('Keep-Alive', 'timeout=25')
            reqUrl.add_header('ContentType', 'application/x-www-form-urlencoded')
            reqUrl.add_header('Connection', 'Keep-Alive')
            urlFile = urllib2.urlopen(reqUrl, timeout=HTTP_ConnectionTimeout)
            fileContent = urlFile.read()
            urlFile.close()
        except Exception, ex:
            self.logCall('File download error, exception: %s, url: %s' % (str(ex), url))
            fileContent = None
            if not strings2.M_TVGUIDE_CLOSING and retryFailed == True and ('HTTP Error 500' in str(ex) or 'HTTP Error 408' in str(ex) or 'timeout' in str(ex) or 'IncompleteRead' in str(ex)):
                return self.downloadUrl(url, retryFailed=False)

        return fileContent

    def parseDOM(self, html, name=u"", attrs={}, ret=False):
        # Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

        if isinstance(html, str):
            try:
                html = [html.decode("utf-8")] # Replace with chardet thingy
            except:
                html = [html]
        elif isinstance(html, unicode):
            html = [html]
        elif not isinstance(html, list):
            return u""

        if not name.strip():
            return u""

        ret_lst = []
        for item in html:
            temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
            for match in temp_item:
                item = item.replace(match, match.replace("\n", " "))

            lst = []
            for key in attrs:
                lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
                if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
                    lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

                if len(lst) == 0:
                    lst = lst2
                    lst2 = []
                else:
                    test = range(len(lst))
                    test.reverse()
                    for i in test:  # Delete anything missing from the next list.
                        if not lst[i] in lst2:
                            del(lst[i])

            if len(lst) == 0 and attrs == {}:
                lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
                if len(lst) == 0:
                    lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

            if isinstance(ret, str):
                lst2 = []
                for match in lst:
                    attr_lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
                    if len(attr_lst) == 0:
                        attr_lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
                    for tmp in attr_lst:
                        cont_char = tmp[0]
                        if cont_char in "'\"":
                            # Limit down to next variable.
                            if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

                            # Limit to the last quotation mark
                            if tmp.rfind(cont_char, 1) > -1:
                                tmp = tmp[1:tmp.rfind(cont_char)]
                        else:
                            if tmp.find(" ") > 0:
                                tmp = tmp[:tmp.find(" ")]
                            elif tmp.find("/") > 0:
                                tmp = tmp[:tmp.find("/")]
                            elif tmp.find(">") > 0:
                                tmp = tmp[:tmp.find(">")]

                        lst2.append(tmp.strip())
                lst = lst2
            else:
                lst2 = []
                for match in lst:
                    endstr = u"</" + name

                    start = item.find(match)
                    end = item.find(endstr, start)
                    pos = item.find("<" + name, start + 1 )

                    while pos < end and pos != -1:
                        tend = item.find(endstr, end + len(endstr))
                        if tend != -1:
                            end = tend
                        pos = item.find("<" + name, pos + 1)

                    if start == -1 and end == -1:
                        temp = u""
                    elif start > -1 and end > -1:
                        temp = item[start + len(match):end]
                    elif end > -1:
                        temp = item[:end]
                    elif start > -1:
                        temp = item[start + len(match):]

                    if ret:
                        endstr = item[end:item.find(">", item.find(endstr)) + 1]
                        temp = match + temp + endstr

                    item = item[item.find(temp, item.find(match)) + len(temp):]
                    lst2.append(temp)
                lst = lst2
            ret_lst += lst

        return ret_lst

class TvCid:
    def __init__(self, cid, name, title, strm = "", img = ""):
        self.cid = cid
        self.name = name
        self.title = title
        self.strm = strm
        self.src = ""
        self.img = img
        self.rtmpdumpLink = None
        self.ffmpegdumpLink = None

class MapString:
    def __init__(self, channelid, titleRegex, strm, src):
        self.channelid = channelid
        self.titleRegex = titleRegex
        self.strm = strm
        self.src = src

    @staticmethod
    def Parse(xmlstr, logCall=deb):
        rstrm = ''
        categories={}
        if logCall:
            logCall('[UPD] Parsowanie pliku mapy')
        io = StringIO.StringIO(xmlstr)
        context = ElementTree.iterparse(io, events=("start", "end"))
        event, root = context.next()
        elements_parsed = 0
        if logCall:
            logCall('[UPD] %-35s %-50s %s' % ('ID' , 'TITLE_REGEX', 'STRM'))
        result = list()
        for event, elem in context:
            if event == "end":
                if elem.tag == "channel":
                    aid    = elem.get("id")
                    atitle = elem.get("title")
                    astrm  = elem.get("strm")
                    if logCall:
                        logCall('[UPD] %-35s %-50s %s' % (aid, atitle, astrm))
                    result.append(MapString(aid, atitle, astrm, ''))
                if elem.tag == "map":
                    rstrm = elem.get("strm")
                if elem.tag == "category":
                    category_tags_set = set()
                    category_name = elem.get("name")
                    category_tags = elem.get("tags").split('|')
                    for tag in category_tags:
                        category_tags_set.add((u'' + tag))
                    categories[category_name] = category_tags_set
        #if logCall:
            #logCall('\n')
            #if rstrm != '':
                #logCall('[UPD] Stream rule = %s' % rstrm)
        return [result, rstrm, categories]

    @staticmethod
    def loadFile(path, logCall=deb):
        try:
            logCall('[UPD] Wczytywanie mapy => mtvguide: %s' % path)
            logCall('\n')
            with open(path, 'r') as content_file:
                content = content_file.read()
        except Exception, ex:
            logCall('loadFile exception: %s' % getExceptionString())
            content = ""
        return content

class SleepSupervisor(object):
    def __init__(self, stopCallback):
        self.stopPlaybackCall = stopCallback
        self.sleepEnabled = ADDON.getSetting('sleep__enabled')
        self.sleepAction = ADDON.getSetting('sleep__action')
        self.sleepTimer = int(ADDON.getSetting('sleep_timer')) * 60 #time in secs
        self.timer = None
        self.actions = {
                        '0': 'PlayerControl(Stop)',
                        '1': 'Quit',
                        '2': 'Powerdown',
                        '3': 'Suspend'
        }
        try:
            self.action = self.actions[self.sleepAction]
        except KeyError:
            self.action = 'PlayerControl(Stop)'
        deb('SleepSupervisor timer init: sleepEnabled %s, sleepAction: %s, sleepTimer: %s' % (self.sleepEnabled, self.action, self.sleepTimer))

    def Start(self):
        if self.sleepEnabled == 'true' and self.sleepTimer > 0:
            self.Stop()
            debug('SleepSupervisor timer Start, action = %s' % self.action)
            self.timer = threading.Timer(self.sleepTimer, self.sleepTimeout)
            self.timer.start()

    def Stop(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None
            debug('SleepSupervisor timer Stop')

    def sleepTimeout(self):
        deb('SleepSupervisor sleepTimeout, executing action: %s' % self.action)
        self.timer = None
        self.stopPlaybackCall()
        xbmc.executebuiltin('%s' % self.action)

class baseServiceUpdater:
    locker = threading.Lock()
    logLocker = threading.Lock()
    baseMapContent = None
    categories = None
    def __init__(self):
        self.sl = ShowList(self.log)
        self.login = ''
        self.password = ''
        self.highQuality = 'true'
        self.url = ''
        self.thread = None
        self.serviceRegex = ''
        self.servicePriority = int(0)
        self.traceList = list()
        self.rstrm = ''
        self.forcePrintintingLog = False
        self.printLogTimer = None
        self.useOnlineMap = True
        self.maxAllowedStreams = 1
        self.addDuplicatesToList = False
        self.addDuplicatesAtBeginningOfList = False
        self.serviceEnabled   = 'false'
        self.baseMapFile      = 'basemap.xml'
        self.adultMapFile     = 'adultmap.xml'
        self.vodMapFile       = 'vodmap.xml'
        self.beneluxMapFile   = 'basemap_benelux.xml'
        self.czechMapFile     = 'basemap_czech.xml'
        self.croatianMapFile  = 'basemap_croatian.xml'
        self.danishMapFile    = 'basemap_danish.xml'
        self.englishMapFile   = 'basemap_english.xml'
        self.frenchMapFile    = 'basemap_french.xml'
        self.germanMapFile    = 'basemap_german.xml'
        self.norwegianMapFile = 'basemap_norwegian.xml'
        self.serbianMapFile   = 'basemap_serbian.xml'
        self.swedishMapFile   = 'basemap_swedish.xml'
        self.usMapFile        = 'basemap_us.xml'
        self.radioMapFile     = 'basemap_radio.xml'
        self.automap = list()
        self.mapsLoaded  = False
        self.channelList = None
        self.channels    = None
        self.refreshingStreams = False
        try:
            self.onlineMapFile = onlineMapPathBase + self.localMapFile
        except:
            self.log('baseServiceUpdater self.localMapFile is not defined!!!')
            self.onlineMapFile = ''
            self.localMapFile  = ''
        try:
            self.serviceRegex  = "service=" + self.serviceName + "&cid=%"
            self.rstrm         = self.serviceRegex + 's'
        except:
            self.log('baseServiceUpdater self.serviceName is not defined!!!')
            self.serviceName   = 'baseService'
            self.serviceRegex  = ''
            self.rstrm         = ''

    def waitUntilDone(self):
        if self.thread is not None:
            return self.thread.join()

    def log(self, message):
        if self.thread is not None and self.thread.is_alive() and self.forcePrintintingLog == False:
            self.traceList.append(self.__class__.__name__ + ' ' + message)
        else:
            deb(self.__class__.__name__ + ' ' + message)

    def printLog(self):
        baseServiceUpdater.logLocker.acquire()
        for trace in self.traceList:
            deb(trace)
        baseServiceUpdater.logLocker.release()
        del self.traceList[:]
        self.traceList = list()

    def loginErrorMessage(self):
        self.log('login error for service: %s' % self.serviceName)
        xbmcgui.Dialog().notification(strings(SERVICE_ERROR), strings(SERVICE_LOGIN_INCORRECT) + self.serviceName, time=15000, sound=True)

    def noPremiumMessage(self):
        self.log('no premium for service: %s' % self.serviceName)
        xbmcgui.Dialog().notification(strings(57034).encode('utf-8'), strings(SERVICE_NO_PREMIUM).encode('utf-8') + ' ' + self.serviceName, time=10000, sound=False)

    def startLoadingChannelList(self):
        if self.thread is None or not self.thread.is_alive():
            self.traceList.append('\n')
            self.traceList.append('##############################################################################################################')
            self.traceList.append('\n')
            self.thread = threading.Thread(name='loadChannelList thread', target = self.loadChannelList)
            self.thread.start()
            self.printLogTimer = threading.Timer(15, self.printLogTimeout)
            self.printLogTimer.start()

    def printLogTimeout(self):
        self.printLogTimer = None
        self.forcePrintintingLog = True
        self.printLog()

    def close(self):
        if self.printLogTimer is not None:
            self.printLogTimer.cancel()
        self.printLog()
        self.forcePrintintingLog = True
        self.refreshingStreams = False

    def unlockService(self):
        pass

    def resetService(self):
        self.automap = list()
        self.channelList = None
        self.mapsLoaded = False
        self.refreshingStreams = True
        self.forcePrintintingLog = False

    def getCategoriesFromMap(self):
        if not baseServiceUpdater.categories:
            self.getBaseMap()
        return baseServiceUpdater.categories

    def getBaseMap(self):
        baseServiceUpdater.locker.acquire()

        self.log('\n')
        if not baseServiceUpdater.baseMapContent:
            baseServiceUpdater.baseMapContent = list()
            baseServiceUpdater.categories = {}

            self.loadSingleBaseMap('base', self.baseMapFile)

            if ADDON.getSetting('XXX_EPG') != "":
                self.loadSingleBaseMap('adult', self.adultMapFile)

            if ADDON.getSetting('VOD_EPG') != "":
                self.loadSingleBaseMap('vod', self.vodMapFile)

            if ADDON.getSetting('showBeneluxChannels') == 'true':
                self.loadSingleBaseMap('benelux', self.beneluxMapFile)

            if ADDON.getSetting('showCzechChannels') == 'true':
                self.loadSingleBaseMap('czech', self.czechMapFile)

            if ADDON.getSetting('showCroatianChannels') == 'true':
                self.loadSingleBaseMap('croatian', self.croatianMapFile)

            if ADDON.getSetting('showDanishChannels') == 'true':
                self.loadSingleBaseMap('danish', self.danishMapFile)

            if ADDON.getSetting('showEnglishChannels') == 'true':
                self.loadSingleBaseMap('english', self.englishMapFile)

            if ADDON.getSetting('showFrenchChannels') == 'true':
                self.loadSingleBaseMap('french', self.frenchMapFile)

            if ADDON.getSetting('showGermanChannels') == 'true':
                self.loadSingleBaseMap('german', self.germanMapFile)

            if ADDON.getSetting('showNorwegianChannels') == 'true':
                self.loadSingleBaseMap('norwegian', self.norwegianMapFile)

            if ADDON.getSetting('showSerbianChannels') == 'true':
                self.loadSingleBaseMap('serbian', self.serbianMapFile)

            if ADDON.getSetting('showSwedishChannels') == 'true':
                self.loadSingleBaseMap('swedish', self.swedishMapFile)

            if ADDON.getSetting('showUsChannels') == 'true':
                self.loadSingleBaseMap('us', self.usMapFile)

            if ADDON.getSetting('showRadioChannels') == 'true':
                self.loadSingleBaseMap('radio', self.radioMapFile)

        else:
            self.log('loading cached base map')

        baseServiceUpdater.locker.release()
        return copy.deepcopy(baseServiceUpdater.baseMapContent)

    def loadSingleBaseMap(self, lang, mapFilePath):
        self.log('Loading %s channel map' % lang)
        onlineMapFilename   = onlineMapPathBase + mapFilePath
        map                 = self.sl.getJsonFromExtendedAPI(onlineMapFilename, max_conn_time=9, http_timeout=5, verbose=False)
        if map:
            self.log('successfully downloaded online %s map file: %s' % (lang, onlineMapFilename))
        else:
            localMapFilename      = os.path.join(pathMapBase, mapFilePath)
            self.log('%s file download failed - using local map: %s' % (lang, localMapFilename))
            map                   = MapString.loadFile(localMapFilename, self.log)
        entries, _, seCat         = MapString.Parse(map, None) #None so content wont be printed in logs
        baseServiceUpdater.baseMapContent.extend(entries)
        for id in seCat:
            if id in baseServiceUpdater.categories:
                baseServiceUpdater.categories[id].update(seCat[id])
            else:
                baseServiceUpdater.categories[id] = seCat[id]


    def loadMapFile(self):
        try:
            if not self.mapsLoaded:
                self.automap = self.getBaseMap()

                if self.useOnlineMap:
                    dedicatedMapfile = self.sl.getJsonFromExtendedAPI(self.onlineMapFile, max_conn_time=6, verbose=False)
                else:
                    dedicatedMapfile = None

                if dedicatedMapfile is None:
                    dedicatedMapFilename = os.path.join(pathMapBase, self.localMapFile)
                    if os.path.isfile(dedicatedMapFilename):
                        if self.useOnlineMap:
                            self.log('loadMapFile: dedicated map download failed - using local map')
                        dedicatedMapfile = MapString.loadFile(dedicatedMapFilename, self.log)
                    else:
                        dedicatedMapfile = None
                        self.log('loadMapFile: dedicated map doesnt exist - using just base map')
                else:
                    self.log('loadMapFile: success downloading online map file: %s' % self.onlineMapFile)

                if dedicatedMapfile:
                    if not self.refreshingStreams:
                        dedicatedMap, rstrm, _ = MapString.Parse(dedicatedMapfile, self.log)
                    else:
                        #Avoid printing content of map to log on every refresh
                        dedicatedMap, rstrm, _ = MapString.Parse(dedicatedMapfile, None)
                    for dedicatedEntry in dedicatedMap:
                        for baseEntry in self.automap:
                            if dedicatedEntry.channelid == baseEntry.channelid:
                                self.automap.remove(baseEntry)
                                break
                    self.automap.extend(dedicatedMap)

                    if not self.rstrm or self.rstrm == '':
                        self.rstrm = rstrm

                self.mapsLoaded = True

        except Exception, ex:
            self.log('loadMapFile: Error %s' % getExceptionString())

    def isChannelListStillValid(self):
        return True

    def getDisplayName(self):
        try:
            return self.serviceDisplayName
        except:
            pass 
        return self.serviceName

    def getBaseChannelList(self, silent=False, returnCopy=True):
        result = list()
        try:
            if self.channelList and self.isChannelListStillValid():
                self.log('getBaseChannelList return cached channel list')
                if returnCopy:
                    return copy.deepcopy(self.channelList)
                else:
                    return self.channelList

            tmpresult = self.getChannelList(silent)
            if len(tmpresult) > 0:
                result = tmpresult

            self.channelList = copy.deepcopy(result)
        except:
            self.log('getBaseChannelList exception: %s' % getExceptionString())
        return result

    def loadChannelList(self):
        try:
            startTime = datetime.datetime.now()
            self.channels = self.getBaseChannelList()
            if len(self.channels) <= 0:
                self.log('loadChannelList error lodaing channel list for service %s - aborting!' % self.serviceName)
                self.close()
                return

            if strings2.M_TVGUIDE_CLOSING:
                self.log('loadChannelList service %s requested abort!' % self.serviceName)
                self.close()
                return

            self.log('Loading channel list took: %s seconds' % (datetime.datetime.now() - startTime).seconds)
            self.loadMapFile()
            self.log('Loading channels and map took: %s seconds' % (datetime.datetime.now() - startTime).seconds)

            self.log('\n')
            self.log('[UPD] Wyszykiwanie STRM')
            self.log('-------------------------------------------------------------------------------------')
            self.log('[UPD]     %-30s %-30s %-20s %-35s' % ('-ID mTvGuide-', '-    Orig Name    -', '-    SRC   -', '-    STRM   -'))

            for x in self.automap[:]:

                if strings2.M_TVGUIDE_CLOSING:
                    self.log('loadChannelList loop service %s requested abort!' % self.serviceName)
                    self.close()
                    return

                if x.strm != '':
                    x.src = 'CONST'
                    self.log('[UPD]     %-30s %-15s %-35s' % (x.channelid, x.src, x.strm))
                    continue
                try:
                    p = re.compile(x.titleRegex, re.IGNORECASE)
                    for y in self.channels:
                        b=p.match(y.title)
                        if (b):
                            if x.strm != '' and self.addDuplicatesToList == True:
                                newMapElement = copy.deepcopy(x)
                                newMapElement.strm = self.rstrm % y.cid

                                y.src = newMapElement.src
                                y.strm = newMapElement.strm
                                self.log('[UPD] [B] %-30s %-30s %-20s %-35s ' % (newMapElement.channelid, y.name, newMapElement.src, newMapElement.strm))
                                if self.addDuplicatesAtBeginningOfList == False:
                                    self.automap.append(newMapElement)
                                else:
                                    self.automap.insert(0, newMapElement)
                            else:
                                x.strm = self.rstrm % y.cid
                                y.strm = x.strm
                                x.src  = self.serviceName
                                y.src = x.src
                                self.log('[UPD]     %-30s %-30s %-20s %-35s ' % (x.channelid, y.name, x.src, x.strm))

                except Exception, ex:
                    self.log('%s Error %s %s' % (x.channelid, x.titleRegex, getExceptionString()))

            self.log('\n')
            self.log('[UPD] Nie wykorzystano STRM nadawanych przez %s programow:' % self.serviceName)
            self.log('-------------------------------------------------------------------------------------')
            for y in self.channels:
                if y.src == '' or y.src != self.serviceName:
                    self.log('[UPD] CID=%-12s NAME=%-40s TITLE=%-40s STRM=%-45s' % (y.cid, y.name, y.title,str(y.strm)))

            self.log("[UPD] Zakonczono analize...")
            self.log('Loading everything took: %s seconds' % (datetime.datetime.now() - startTime).seconds)
            self.log('\n')

        except Exception, ex:
            self.log('loadChannelList Error %s' % getExceptionString())
        self.close()

    def getChannel(self, cid):
        try:
            channels = self.getBaseChannelList(silent=True, returnCopy=False)
            for chann in channels:
                if chann.cid == cid:
                    return self.getChannelStream(copy.deepcopy(chann))
            self.log('ERROR getChannel not found cid: %s in channel list!' % cid)
        except:
            self.log('getChannel exception: %s' % getExceptionString())
        return None
