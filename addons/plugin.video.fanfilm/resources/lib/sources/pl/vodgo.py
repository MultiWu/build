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

from resources.lib.libraries import client, cleantitle, cache, source_utils


class source:
    def __init__(self):

        self.priority = 1
        self.language = ['pl']
        self.domains = ['VODGO']
        self.base_link = 'https://vodgo.pl'
        self.search_link = 'https://vodgo.pl/search?query=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year)

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        return tvshowtitle, localtvshowtitle, year

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        return self.search_ep(url, season, episode)

    def contains_word(self, str_to_check, word):
        if str(word).lower() in str(str_to_check).lower():
            return True
        return False

    def contains_all_words(self, str_to_check, words):
        for word in words:
            if not self.contains_word(str_to_check, word):
                return False
        return True

    def search_ep(self, tvshow, season, episode):
        try:
            title = tvshow[0]
            localtitle = tvshow[1]
            year = tvshow[2]
            titles = []
            title2 = title.split('.')[0]
            localtitle2 = localtitle.split('.')[0]
            titles.append(cleantitle.normalize(cleantitle.getsearch(title2)))
            titles.append(cleantitle.normalize(cleantitle.getsearch(localtitle2)))
            titles.append(title2)
            titles.append(localtitle2)

            season_episode = "S%02dE%02d" % (int(season), int(episode))

            for title in titles:
                result = client.request(self.search_link % title.replace(" ", "+"))

                result = client.parseDOM(result, 'div', attrs={'class': "col-9 col-md-10 col-lg-11"})
                for item in result:
                    try:
                        link = client.parseDOM(item, 'a', ret='href')[0]
                        tytul = client.parseDOM(item, 'div')[0]
                        words = title.lower().split(" ")
                        if self.contains_all_words(tytul, words) and year in tytul:
                            result2 = client.request(self.base_link + link)
                            test = client.parseDOM(result2, 'div', attrs={'id': "s%s" % season})
                            links = client.parseDOM(test, 'a', ret='href')
                            for link in links:
                                if season_episode.lower() in link:
                                    return self.base_link + link
                    except:
                        continue
            return
        except Exception as e:
            print(e)
            return

    def search(self, title, localtitle, year):
        try:
            titles = []
            title2 = title.split('.')[0]
            localtitle2 = localtitle.split('.')[0]
            titles.append(cleantitle.normalize(cleantitle.getsearch(title2)))
            titles.append(cleantitle.normalize(cleantitle.getsearch(localtitle2)))
            titles.append(title2)
            titles.append(localtitle2)

            for title in titles:
                result = client.request(self.search_link % title.replace(" ", "+"))

                result = client.parseDOM(result, 'div', attrs={'class': "col-9 col-md-10 col-lg-11"})
                for item in result:
                    try:
                        link = client.parseDOM(item, 'a', ret='href')[0]
                        tytul = client.parseDOM(item, 'div')[0]
                        words = title.lower().split(" ")
                        if self.contains_all_words(tytul, words) and year in tytul:
                            return self.base_link + link
                    except:
                        continue
            return
        except Exception as e:
            print(e)
            return

    def get_lang_by_type(self, lang_type):
        if "dubbing" in lang_type.lower():
            if "kino" in lang_type.lower():
                return 'pl', 'Dubbing Kino'
            return 'pl', 'Dubbing'
        elif 'napisy pl' in lang_type.lower():
            return 'pl', 'Napisy'
        elif 'napisy' in lang_type.lower():
            return 'pl', 'Napisy'
        elif 'lektor pl' in lang_type.lower():
            return 'pl', 'Lektor'
        elif 'lektor' in lang_type.lower():
            return 'pl', 'Lektor'
        elif 'POLSKI' in lang_type.lower():
            return 'pl', None
        elif 'pl' in lang_type.lower():
            return 'pl', None
        return 'en', None

    def sources(self, url, hostDict, hostprDict):
        import re, requests
        s = requests.Session()
        sources = []
        try:
            if url == None: return sources
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
                       'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'Cache-Control': 'max-age=0', 'TE': 'Trailers', }
            result = s.get(url, headers=headers).text
            navigation = client.parseDOM(result, 'ul', attrs={'class': "nav nav-pills"})
            navigation = client.parseDOM(navigation, 'li', attrs={'class': "nav-item"})
            for item in navigation:
                try:
                    nazwa = client.parseDOM(item, 'a')[0]
                    link = client.parseDOM(item, 'a', ret='href')[0]
                    lang, info = self.get_lang_by_type(nazwa)
                    result2 = s.get(url + link, headers=headers).text
                    result2 = client.parseDOM(result2, 'li', attrs={'class': "list-group-item bg-black p-0 mt-1"})
                except:
                    continue
                for item2 in result2:
                    try:
                        token = re.findall("_token\" value=\"(.*?)\"", item2)[0]
                        hash = re.findall("onclick=set_url\(\"(.*?)\"", item2)[0]
                        test2 = s.get("https://vodgo.pl/frame?url=%s&token=%s" % (hash, token)).text
                        video_link = client.parseDOM(test2, 'iframe', ret='src')[0]
                        if "wysoka" in item2:
                            quality = "HD"
                        else:
                            quality = "SD"
                        valid, host = source_utils.is_host_valid(video_link, hostDict)
                        if valid:
                            sources.append(
                                {'source': host, 'quality': quality, 'language': lang, 'url': video_link, 'info': info,
                                 'direct': False, 'debridonly': False})
                        else:
                            continue
                    except:
                        continue
            return sources
        except:
            return sources

    def resolve(self, url):
        return url
