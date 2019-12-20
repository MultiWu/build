# -*- coding: utf-8 -*-

'''
    Covenant Add-on
    Copyright (C) 2018 CherryTeam

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib

try:
    import urlparse
except BaseException:
    import urllib.parse as urlparse

import requests
from resources.lib.libraries import source_utils, client, cleantitle, control, cache
from resources.lib.libraries import more_sources


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['pl']
        self.domains = ['segos.es']
        self.user_name = control.setting('segos.username')
        self.user_pass = control.setting('segos.password')
        self.base_link = 'http://segos.es'
        self.search_link = '/?search=%s'
        self.session = requests.Session()
        self.useragent = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.40 Mobile Safari/537.36"

    def contains_word(self, str_to_check, word):
        if str(word).lower() in str(str_to_check).lower():
            return True
        return False

    def contains_all_words(self, str_to_check, words):
        for word in words:
            if not self.contains_word(str_to_check, word):
                return False
        return True

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year)

    def search(self, title, localtitle, year):
        try:
            titles = []
            title2 = title.split('.')[0]
            localtitle2 = localtitle.split('.')[0]
            titles.append(cleantitle.normalize(cleantitle.getsearch(title2)))
            titles.append(cleantitle.normalize(cleantitle.getsearch(localtitle2)))
            titles.append(title2)
            titles.append(localtitle2)

            cookies = client.request('http://segos.es', output='cookie')
            cache.cache_insert('segos_cookie', cookies)
            for title in titles:
                try:
                    query = self.search_link % urllib.quote_plus(title.replace(" ", "+"))
                    url = urlparse.urljoin(self.base_link, query)

                    result = client.request(url, headers={'Cookie': cookies})

                    results = client.parseDOM(result, 'div', attrs={'class': 'col-lg-12 col-md-12 col-xs-12'})
                except BaseException:
                    continue
                for result in results:
                    try:
                        segosurl = client.parseDOM(result, 'a', ret='href')[0]
                        result = client.parseDOM(result, 'a')
                        segostitles = cleantitle.normalize(cleantitle.getsearch(result[1])).split('/')
                        segostitles.append(result[1])
                        rok = str(result[1][-5:-1])
                    except BaseException:
                        continue
                    for segostitle in segostitles:
                        try:
                            segostitle = segostitle.replace("  ", " ")
                            simply_name = title.replace("  ", " ")
                            words = simply_name.split(" ")
                            if self.contains_all_words(segostitle, words) and year == rok:
                                link = urlparse.urljoin(self.base_link, segosurl)
                                return link
                            continue
                        except BaseException:
                            continue
        except Exception as e:
            print(str(e))
            return

    def search_ep(self, titles, season, episode):
        try:
            for title in titles:
                simply_name = cleantitle.normalize(cleantitle.getsearch(title))
                query = self.search_link % str(title).replace(" ", "+")
                url = urlparse.urljoin(self.base_link, query)

                cookies = client.request(self.base_link, output='cookie')
                cache.cache_insert('segos_cookie', cookies)
                result = client.request(url, headers={'Cookie': cookies})

                results = client.parseDOM(result, 'div', attrs={'class': 'col-lg-12 col-md-12 col-xs-12'})
                for result in results:
                    try:
                        segosurl = client.parseDOM(result, 'a', ret='href')[0]
                        segosurl = segosurl + "&s=%s&o=%s" % (season, episode)
                        result = client.parseDOM(result, 'a')
                        segostitles = cleantitle.normalize(cleantitle.getsearch(result[1])).split('/')
                    except BaseException:
                        continue
                    for segostitle in segostitles:
                        try:
                            segostitle = segostitle.replace("  ", " ")
                            simply_name = simply_name.replace("  ", " ")
                            words = simply_name.split(" ")
                            if self.contains_all_words(segostitle, words):
                                if 'seriale' in segosurl:
                                    link = urlparse.urljoin(self.base_link, segosurl)
                                    return link
                        except BaseException:
                            continue
                        continue
        except BaseException:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        return {tvshowtitle, localtvshowtitle}

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        return self.search_ep(url, season, episode)

    def sources(self, url, hostDict, hostprDict):
        useragent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0"
        sources = []
        try:
            if url is None:
                return sources
            try:
                cookies = cache.cache_get('segos_cookie')['value']
            except:
                cookies = client.request('https://segos.es', output='cookie')
            data = {"login": self.user_name, 'password': self.user_pass, 'loguj': ''}
            # cookies2 = client.request('https://segos.es/?page=login', post=data, headers={'Cookie': str(cookies)})
            # headers={'Cookie': cookies}, output='cookie')
            cookies2 = '; '.join(['%s=%s' % (i.name, i.value) for i in requests.post('https://segos.es/?page=login', data=data, headers={'Cookie': cookies, 'User-Agent': useragent}).cookies])
            cookies = cookies + "; " + cookies2
            result = client.request(url, headers={'Cookie': cookies})
            result = client.parseDOM(result, 'table', attrs={'class': 'table table-hover table-bordered'})
            results = client.parseDOM(result, 'tr')
            quality = 'SD'
            for result in results:
                try:
                    try:
                        quality = client.parseDOM(result, 'td')[1]
                    except BaseException:
                        pass
                    quality = quality.replace(' [EXTENDED]', '').replace(' [Extended]', '')
                    lang = 'en'
                    info = client.parseDOM(result, 'td')[0]
                    info = client.parseDOM(info, 'img', ret='src')
                    if 'napisy' in info[0]:
                        info[0] = 'Napisy'
                        lang = 'pl'
                    if 'lektor' in info[0]:
                        info[0] = 'Lektor'
                        lang = 'pl'
                    if 'dubbing' in info[0]:
                        info[0] = 'Dubbing'
                        lang = 'pl'
                    link = client.parseDOM(result, 'a', ret='href')
                    link = urlparse.urljoin(self.base_link, str(link[0]))
                    k = client.request(link, headers={'Cookie': cookies})
                    video_link_direct = ''
                    video_link_content = k
                    video_link_content = client.parseDOM(video_link_content, 'div', attrs={'class': 'embed-responsive embed-responsive-16by9'})
                    try:
                        video_link = client.parseDOM(video_link_content, 'iframe', ret='src')[0]
                    except BaseException:
                        video_link_direct = client.parseDOM(video_link_content, 'source', ret='src')[0]
                        video_link = ''
                    if video_link_direct:
                        video_link = video_link_direct
                        host = 'Segos.es'
                    else:
                        valid, host = source_utils.is_host_valid(video_link, hostDict)
                    more = False
                    for source in more_sources.more_cdapl(video_link, hostDict, lang, info[0]):
                        sources.append(source)
                        more = True
                    for source in more_sources.more_rapidvideo(video_link, hostDict, lang, info[0]):
                        sources.append(source)
                        more = True
                    if not more:
                        if 'ebd' in host.lower():
                            host = 'CDA'
                        if 'segos' in video_link:
                            headers = {"Cookie": cookies}
                            helper = '|%s' % '&'.join(['%s=%s' % (key, urllib.quote_plus(headers[key])) for key in headers])
                            sources.append({'source': host, 'quality': quality, 'language': lang, 'url': video_link + helper, 'info': info[0], 'direct': True, 'debridonly': False})
                        else:
                            sources.append({'source': host, 'quality': quality, 'language': lang, 'url': video_link, 'info': info[0], 'direct': False, 'debridonly': False})
                except BaseException:
                    continue
            return sources
        except Exception as e:
            return sources

    def resolve(self, url):
        if 'Cookie' in url:
            headers = requests.utils.default_headers()
            return url + "&User-Agent=" + headers['User-Agent']
        else:
            return url
