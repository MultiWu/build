#      Copyright (C) 2018 Mariusz Brychcy
#      Copyright (C) 2016 Andrzej Mleczko

import urllib, copy, re
import xbmc, xbmcgui, xbmcvfs
from strings import *
from serviceLib import *

serviceName   = 'playlist'

class PlaylistUpdater(baseServiceUpdater):
    def __init__(self, instance_number):
        self.serviceName        = serviceName + "_%s" % instance_number
        self.instance_number    = str(instance_number)
        self.localMapFile       = 'playlistmap.xml'
        baseServiceUpdater.__init__(self)
        self.servicePriority    = int(ADDON.getSetting('%s_priority' % self.serviceName))
        self.serviceDisplayName = ADDON.getSetting('%s_display_name' % self.serviceName)
        self.source             = ADDON.getSetting('%s_source'       % self.serviceName)
        self.addDuplicatesToList = True
        self.useOnlineMap       = False

        if int(instance_number) <= int(ADDON.getSetting('nr_of_playlists')):
            self.serviceEnabled  = ADDON.getSetting('%s_enabled'     % self.serviceName)
        else:
            self.serviceEnabled = 'false'

        if self.source == 'Url':
            self.url = ADDON.getSetting('%s_url' % self.serviceName)
        else:
            self.url = xbmc.translatePath(ADDON.getSetting('%s_file' % self.serviceName))

        if ADDON.getSetting('%s_high_prio_hd' % self.serviceName) == 'true':
            self.hdStreamFirst = True
        else:
            self.hdStreamFirst = False

        if ADDON.getSetting('%s_stop_when_starting' % self.serviceName) == 'true':
            self.stopPlaybackOnStart = True
        else:
            self.stopPlaybackOnStart = False

    def downloadPlaylist(self, path):
        content = None
        start_time = datetime.datetime.now()
 
        while (content is None or content == '') and (datetime.datetime.now() - start_time).seconds < 10:
            try:
                content = self.sl.getJsonFromExtendedAPI(path)
            except Exception as ex:
                self.log('downloadPlaylist Error %s' % getExceptionString())

            if (content is None or content == '') and (datetime.datetime.now() - start_time).seconds < 10:
                self.log('downloadPlaylist Failed, sleeping')
                time.sleep(0.5)

        return content


    def getPlaylistContent(self, path, urltype):
        content = ''
        try:
            self.log('getPlaylistContent opening playlist: %s, urltype: %s' % (path, urltype))
            if urltype == 'Url':
                tmpcontent = self.downloadPlaylist(path)

                if tmpcontent is None or tmpcontent == '':
                    raise Exception
            else:
                try:
                    tmpcontent = open(path, 'r').read()
                except:
                    self.log('getPlaylistContent opening normally Error %s, type: %s, url: %s' % (getExceptionString(), urltype, path) )
                    self.log('getPlaylistContent trying to open file using xbmcvfs')
                    lf = xbmcvfs.File(path)
                    tmpcontent = lf.read()
                    lf.close()
                    if tmpcontent is None or tmpcontent == "":
                        raise Exception

            content = tmpcontent
        except:
            self.log('getPlaylistContent opening Error %s, type: %s, url: %s' % (getExceptionString(), urltype, path) )
            xbmcgui.Dialog().notification(strings(59905).encode('utf-8'), strings(57049).encode('utf-8') + ' ' + self.serviceName + ' (' + self.getDisplayName() + ') ' + strings(57050).encode('utf-8'), time=10000, sound=False)
        return content

    def getChannelList(self, silent):
        result = list()
        try:
            regexReplaceList = list()

            sdList = list()
            hdList = list()
            fhdList = list()
            uhdList = list()

            cleanup_regex      =     re.compile("\[COLOR\s*\w*\]|\[/COLOR\]|\[B\]|\[/B\]|\[I\]|\[/I\]|^\s*|\s*$",  re.IGNORECASE)

            regexReplaceList.append( re.compile('[^A-Za-z0-9+/:]+',                                                re.IGNORECASE) )
            regexReplaceList.append( re.compile('\sL\s',                                                           re.IGNORECASE) )
            regexReplaceList.append( re.compile('(\s|^)(Feed|NY|New\sYork|LA|Los\sAngeles|San\sDiego|Europe|SD|FULL|ADULT:|EXTRA:|VIP:|VIP|Audio|Backup|Multi|Sub|VIASAT:|XXX|XXX:)(?=\s|$)',  re.IGNORECASE) )

            langReplaceList = list()
            regexRemoveList = list()

            langReplaceList.append({ 'regex' : re.compile('(\s|^)(pl/en|Polska|Poland|PL:?)(?=\s|$)|^(PL:)', re.IGNORECASE), 'lang' : 'PL'})
            regexRemoveList.append( re.compile('(\s|^)(L\s*)?(AE|AF|AFG|AFR|AL|AO|AR|ARB(\s*Sport(s)?)?|AT|AU|AZ|BD|BF|BG|BH|BJ|BR|CA|CG|CH|CM|CN|CR|CY|DZ|EE|EG|ES|FI|GA|GH|GN|GR|HN|HU|ID|IL|IN|IQ|IR|IS|IT|JO|KE|KRD|KW|LAM|LB|LE|LT|LU|LY|Latin\s*America|MA|MK|ML|MN|MT|MX|MY|NG|OM|PH|PK|PT|QA|RO|RO/HU|RS|RU|SA|SAC|SC|SI|SL|SN|SO|SY|TD|TH|TN|TR|UA|VN|YE|ZA|19\d\d|20\d\d|S\s*\d\d\s*E\s*\d\d)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showBeneluxChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(BE:?|NL:?)(?=\s|$)|^(BE:|NL:)', re.IGNORECASE), 'lang' : 'BE'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(BE|NL)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showCzechChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(CZ:?)(?=\s|$)|^(CZ:)', re.IGNORECASE), 'lang' : 'CZ'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(CZ)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showCroatianChannels') == 'true' or ADDON.getSetting('showSerbianChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(CRO:?|HR:?|HRV:?|Hrvatska|SRB:?|Srbija|BH:?|Bosna|SLO:?|Slovenija|SR:?|Crna\s*Gora)(?=\s|$)|^(CRO:|HR:|HRV:|SRB:|SLO:|SR:)', re.IGNORECASE), 'lang' : 'CRO'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(CRO|HR|SRB|SLO|SR|Yu)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showDanishChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(Danmark|Denmark|DK:?|Nordic|Scandinavia)(?=\s|$)|^(DK:)', re.IGNORECASE), 'lang' : 'DK'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(DK)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showEnglishChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(UK:?)(?=\s|$)|^(UK:)', re.IGNORECASE), 'lang' : 'UK'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(UK)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showFrenchChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(FR:?)(?=\s|$)|^(FR:)', re.IGNORECASE), 'lang' : 'FR'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(FR)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showGermanChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(DE:?)(?=\s|$)|^(DE:)', re.IGNORECASE), 'lang' : 'DE'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(DE)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showNorwegianChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(Norge|Norway|NO:?|Nordic|Scandinavia)(?=\s|$)|^(NO:)', re.IGNORECASE), 'lang' : 'NO'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(NO)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showSwedishChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(Sverige|Sweden|SE:?|Nordic|Scandinavia)(?=\s|$)|^(SE:)', re.IGNORECASE), 'lang' : 'SE'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(SE)(?=\s|$)', re.IGNORECASE) )

            if ADDON.getSetting('showUsChannels') == 'true':
                langReplaceList.append({ 'regex' : re.compile('(\s|^)(USA|US:?)(?=\s|$)|^(US:)', re.IGNORECASE), 'lang' : 'US'})
            else:
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?(USA|US)(?=\s|$)', re.IGNORECASE) )


            regexHD            =     re.compile('(\s|^)(720p|720|HD\sHD|HD)(?=\s|$)',                              re.IGNORECASE)
            regexFHD           =     re.compile('(\s|^)(FHD|1080p|1080)(?=\s|$)',                                  re.IGNORECASE)
            regexUHD           =     re.compile('(\s|^)(4K|UHD)(?=\s|$)',                                          re.IGNORECASE)

            regex_chann_name   =     re.compile('tvg-id="[^"]*"',                                                  re.IGNORECASE)
            if ADDON.getSetting('VOD_EPG') == "":
                regexCorrectStream =     re.compile('^(plugin|http|rtmp)(?!.*?[.](mp4|mkv|avi|mov|wma))',                 re.IGNORECASE)
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?((?i)VOD)(?=\s|$)', re.IGNORECASE) )
            else:
                regexCorrectStream =     re.compile('^plugin|http|^rtmp',                                                 re.IGNORECASE)

            if ADDON.getSetting('XXX_EPG') == "":
                regexRemoveList.append( re.compile('(\s|^)(L\s*)?((?i)Adult)(?=\s|$)', re.IGNORECASE) )

            title = None
            nextFreeCid = 0
            self.log('\n\n')
            self.log('[UPD] Pobieram liste dostepnych kanalow dla serwisu %s' % self.serviceName)
            self.log('[UPD] -------------------------------------------------------------------------------------')
            self.log('[UPD] %-10s %-35s %-35s' % ( '-CID-', '-NAME-', '-STREAM-'))

            channelsArray = self.getPlaylistContent(self.url.strip(), self.source)

            if channelsArray is not None and channelsArray != "" and len(channelsArray) > 0:
                cleaned_playlist = cleanup_regex.sub('', channelsArray)
                for line in cleaned_playlist.splitlines():
                    stripLine = line.strip()

                    if '#EXTINF:' in stripLine:
                        tmpTitle = ''
                        title = ''
                        splitedLine = stripLine.split(',')
                        if len(splitedLine) > 1:
                            tmpTitle = splitedLine[len(splitedLine) - 1].strip()
                        if tmpTitle == '':
                            match = regex_chann_name.findall(stripLine)
                            if len(match) > 0:
                                tmpTitle = match[0].replace("tvg-id=","").replace('"','').strip()

                        if tmpTitle is not None and tmpTitle != '':
                            title = tmpTitle
                            HDStream = False
                            FHDStream = False
                            UHDStream = False

                            for regexReplace in regexReplaceList:
                                title = regexReplace.sub(' ', title)

                            title, match = regexUHD.subn(' UHD ', title)
                            if match > 0:
                                UHDStream = True

                            title, match = regexFHD.subn(' HD ', title)
                            if match > 0:
                                FHDStream = True

                            title, match = regexHD.subn(' HD ', title)
                            if match > 0:
                                HDStream = True

                            for langReplaceMap in langReplaceList:
                                title, match = langReplaceMap['regex'].subn('', title)
                                if match > 0:
                                    title += ' ' + langReplaceMap['lang']

                            for regexRemove in regexRemoveList:
                                if( regexRemove.search(title) ):
                                    title = ''
                            title = title.replace('  ', ' ').strip()

                    elif title is not None and regexCorrectStream.match(stripLine):
                        if title != '':
                            channelCid = str(nextFreeCid)
                            if UHDStream:
                                channelCid = channelCid + '_UHD'
                                uhdList.append(TvCid(channelCid, title, title, stripLine, ''))
                            elif FHDStream:
                                channelCid = channelCid + '_FHD'
                                fhdList.append(TvCid(channelCid, title, title, stripLine, ''))
                            elif HDStream:
                                channelCid = channelCid + '_HD'
                                hdList.append(TvCid(channelCid, title, title, stripLine, ''))
                            else:
                                sdList.append(TvCid(channelCid, title, title, stripLine, ''))

                            self.log('[UPD] %-10s %-35s %-35s' % (channelCid, title, stripLine))
                            nextFreeCid = nextFreeCid + 1
                        #else:
                            #self.log('[UPD] %-10s %-35s %-35s' % ('-', 'No title!', stripLine))

            if self.hdStreamFirst:
                result = uhdList
                result.extend(fhdList)
                result.extend(hdList)
                result.extend(sdList)
            else:
                result = sdList
                result.extend(hdList)
                result.extend(fhdList)
                result.extend(uhdList)

        except Exception as ex:
            self.log('getChannelList Error %s' % getExceptionString())
        return result

    def getChannelStream(self, chann):
        try:
            if self.stopPlaybackOnStart and xbmc.Player().isPlaying():
                xbmc.Player().stop()
                xbmc.sleep(500)
            self.log('getChannelStream: found matching channel: cid %s, name %s, stream %s' % (chann.cid, chann.name, chann.strm))

            try:
                reqUrl   = urllib2.Request(chann.strm)
                reqUrl.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20121213 Firefox/19.0')
                reqUrl.add_header('Keep-Alive', 'timeout=20')
                reqUrl.add_header('ContentType', 'application/x-www-form-urlencoded')
                reqUrl.add_header('Connection', 'Keep-Alive')
                new_url = urllib2.urlopen(reqUrl, timeout=5).geturl()
                if new_url != chann.strm:
                    self.log('Http request returned new stream url: %s' % new_url)
                    new_chann = copy.deepcopy(chann)
                    new_chann.strm = new_url
                    return new_chann

            except Exception as ex:
                self.log('Exception while trying to get redirect url: %s' % getExceptionString())

            return chann

        except Exception as ex:
            self.log('getChannelStream Error %s' % getExceptionString())
        return None

    def log(self, message):
        if self.thread is not None and self.thread.is_alive() and self.forcePrintintingLog == False:
            self.traceList.append(self.__class__.__name__ + '_' + self.instance_number + ' ' + message)
        else:
            deb(self.__class__.__name__ + '_' + self.instance_number + ' ' + message)