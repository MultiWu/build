# -*- coding: utf-8 -*-
'''
    Covenant Add-on
    Copyright (C) 2018 :)

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

import requests

try:
    import urlparse
except:
    import urllib.parse as urlparse
try:
    import HTMLParser
    from HTMLParser import HTMLParser
except:
    from html.parser import HTMLParser
try:
    import urllib2
except:
    import urllib.request as urllib2

from resources.lib.libraries import source_utils, control
from resources.lib.libraries import cleantitle
from resources.lib.libraries import client
from ptw.debug import log_exception


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['pl']
        self.domains = ['zalukaj.com']

        self.base_link = 'https://zalukaj.com/'
        self.search_link = 'https://zalukaj.com/v2/ajax/load.search?html=1&q=%s'
        self.user_name = control.setting('zalukaj.username')
        self.user_pass = control.setting('zalukaj.password')
        self.session = requests.Session()

    def contains_word(self, str_to_check, word):
        if str(word).lower() in str(str_to_check).lower():
            return True
        return False

    def contains_all_words(self, str_to_check, words):
        for word in words:
            if not self.contains_word(str_to_check, word):
                return False
        return True

    def search(self, title, localtitle, year, is_movie_search):
        try:
            titles = []
            titles.append(cleantitle.normalize(cleantitle.getsearch(title)))
            titles.append(cleantitle.normalize(cleantitle.getsearch(localtitle)))

            # data = {'login': self.user_name, 'password': self.user_pass}
            # result = self.session.post('https://zalukaj.com/account.php', headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36"}, data=data)
            headers = {
                'Cookie': '__cfduid=d61b42b729455a590ff291892cb688ea11546349293; PHPSESSID=7u6cbc5pagnhqfm84jgjhg9hc2; __PHPSESSIDS=de81fa674b436a948cb337b7f4d2fa3898bd308c'}
            for title in titles:
                url = self.search_link % str(title).replace(" ", "+")
                result = self.session.get(url, headers=headers).content
                result = result.decode('utf-8')
                h = HTMLParser()
                result = h.unescape(result)
                result = client.parseDOM(result, 'div', attrs={'class': 'row'})

                for item in result:
                    try:
                        link = str(client.parseDOM(item, 'a', ret='href')[0])
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = self.base_link + link
                        nazwa = str(client.parseDOM(item, 'a', ret='title')[0])
                        name = cleantitle.normalize(cleantitle.getsearch(nazwa))
                        name = name.replace("  ", " ")
                        title = title.replace("  ", " ")
                        words = title.split(" ")
                        if self.contains_all_words(name, words) and str(year) in link:
                            return link
                    except:
                        continue
        except Exception as e:
            log_exception()
            return

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year, True)

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        titles = (tvshowtitle, localtvshowtitle)
        return titles, year

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        return self.search_ep(url[0], season, episode, url[1])  # url = titles & year

    def search_ep(self, titles, season, episode, year):
        try:
            # data = {'login': self.user_name, 'password': self.user_pass}
            # result = self.session.post('https://zalukaj.com/account.php', headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36"}, data=data)
            headers = {
                'Cookie': '__cfduid=d61b42b729455a590ff291892cb688ea11546349293; PHPSESSID=7u6cbc5pagnhqfm84jgjhg9hc2; __PHPSESSIDS=de81fa674b436a948cb337b7f4d2fa3898bd308c'}
            query = 'S{:02d}E{:02d}'.format(int(season), int(episode))
            for title in titles:
                title = cleantitle.normalize(cleantitle.getsearch(title))
                result = self.session.get(self.base_link, headers=headers).content
                result = client.parseDOM(result, 'td', attrs={'class': 'wef32f'})
                for row in result:
                    try:
                        tytul = client.parseDOM(row, 'a', ret='title')[0]
                    except:
                        continue
                    tytul = cleantitle.normalize(cleantitle.getsearch(tytul)).replace("  ", " ")
                    words = title.split(" ")
                    if self.contains_all_words(tytul, words):
                        link = self.base_link + client.parseDOM(row, 'a', ret='href')[0]
                        content = self.session.get(link, headers=headers).content
                        content = client.parseDOM(content, 'div', attrs={'id': 'sezony'})
                        for item in content:
                            if 'Sezon: %s' % str(season) in item:
                                link = self.base_link + client.parseDOM(item, 'a', ret='href')[0]
                                content = self.session.get(link, headers=headers).content
                                content = client.parseDOM(content, 'div', attrs={'class': 'sezony'})
                                for item in content:
                                    if query in item:
                                        link = client.parseDOM(item, 'a', ret='href')[0]
                                        return link
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            # data = {'login': self.user_name, 'password': self.user_pass}
            # result = self.session.post('https://zalukaj.com/account.php', headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36"}, data=data)
            headers = {
                'Cookie': '__cfduid=d61b42b729455a590ff291892cb688ea11546349293; PHPSESSID=7u6cbc5pagnhqfm84jgjhg9hc2; __PHPSESSIDS=de81fa674b436a948cb337b7f4d2fa3898bd308c'}
            if url.startswith('//'):
                url = "https:" + url
            sources = []
            if url == None: return sources
            url = url
            result = self.session.get(url, headers=headers).content
            link = "https://zalukaj.com" + str(client.parseDOM(result, 'iframe', ret='src')[0]) + "&x=1"
            details = str(client.parseDOM(result, 'div', attrs={'class': 'details'})[0])
            lang, info = self.get_lang_by_type(str(details))
            result = self.session.get(link, headers=headers).content
            try:
                url = str(client.parseDOM(result, 'source', ret='src')[0])
                valid, host = source_utils.is_host_valid(url, hostDict)
                sources.append(
                    {'source': host, 'quality': 'HD', 'language': lang, 'url': url, 'info': info, 'direct': True,
                     'debridonly': False})
                return sources
            except:
                url = str(client.parseDOM(result, 'iframe', ret='src')[0])
                valid, host = source_utils.is_host_valid(url, hostDict)
                sources.append(
                    {'source': host, 'quality': 'HD', 'language': lang, 'url': url, 'info': info, 'direct': False,
                     'debridonly': False})
                return sources
        except:
            log_exception()
            return sources

    def get_lang_by_type(self, lang_type):
        if "dubbing" in lang_type.lower():
            if "kino" in lang_type.lower():
                return 'pl', 'Dubbing Kino'
            return 'pl', 'Dubbing'
        elif 'lektor pl' in lang_type.lower():
            return 'pl', 'Lektor'
        elif 'lektor' in lang_type.lower():
            return 'pl', 'Lektor'
        elif 'napisy pl' in lang_type.lower():
            return 'pl', 'Napisy'
        elif 'napisy' in lang_type.lower():
            return 'pl', 'Napisy'
        elif 'POLSKI' in lang_type.lower():
            return 'pl', None
        elif 'pl' in lang_type.lower():
            return 'pl', None
        return 'en', None

    def resolve(self, url):
        link = str(url).replace("//", "/").replace(":/", "://").split("?")[0]
        return str(link)
