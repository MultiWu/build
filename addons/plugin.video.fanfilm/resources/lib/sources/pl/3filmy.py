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

from resources.lib.libraries import client, cleantitle, cache
import json, re

try:
    import HTMLParser
    from HTMLParser import HTMLParser
except:
    from html.parser import HTMLParser
try:
    import urlparse
except:
    import urllib.parse as urlparse
try:
    import urllib2
except:
    import urllib.request as urllib2


class source:
    def __init__(self):

        self.priority = 1
        self.language = ['pl']
        self.domains = ['3filmy.com']
        self.base_link = 'https://3filmy.com'
        self.search_link = 'https://3filmy.com/ajax/search?q=%s'

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
                result = client.request(self.search_link % title)

                result = json.loads(result)
                for item in result:
                    try:
                        rok = item['d']
                        link = item['link'].replace("\/", "/")
                        tytul = item['t']
                        words = title.lower().split(" ")
                        if self.contains_all_words(tytul, words) and year in rok:
                            link = self.base_link + link
                            result2 = client.request(link)
                            result2 = client.parseDOM(result2, 'div', attrs={'class': "se-c"})
                            test = client.parseDOM(result2, 'li', ret='data-id')
                            result2 = client.parseDOM(result2, 'li')
                            for item2, id in zip(result2, test):
                                if season_episode in item2:
                                    return link + client.parseDOM(item2, 'a', ret='href')[0] + "|" + id
                    except Exception as e:
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
                result = client.request(self.search_link % title)

                result = json.loads(result)
                for item in result:
                    try:
                        rok = item['d']
                        link = item['link'].replace("\/", "/")
                        tytul = item['t']
                        words = title.lower().split(" ")
                        if self.contains_all_words(tytul, words) and year in rok:
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
        sources = []
        data_id = ''
        tvshow = False
        try:
            if url == None: return sources
            try:
                data_id = url.split("|")[1]
            except:
                pass
            url = url.split("|")[0]
            result = client.request(url)
            data_hash = re.findall("data-hash=\"(.*?)\"", result)[0]
            if not data_id:
                data_id = url.split(".html")[0].split("-")[-1]
                test = json.loads(
                    client.request("https://3filmy.com/ajax/video.details", post={'id': data_id, 'hash': data_hash}))
            else:
                tvshow = True
                test = json.loads(
                    client.request("https://3filmy.com/ajax/video.details", post={'id': data_id, 'hash': data_hash, 'ep': "true"}))
            from urllib import unquote
            highest_quality = test['q_avb'][0]
            if not tvshow:
                test = json.loads(
                    client.request("https://3filmy.com/ajax/video.details", post={'id': data_id, 'hash': data_hash, 'q': highest_quality}))
            else:
                test = json.loads(
                    client.request("https://3filmy.com/ajax/video.details", post={'id': data_id, 'hash': data_hash, 'q': highest_quality, 'ep': "true"}))
            url = unquote(test['link']).decode('utf8')
            url = do_xor("5d", url)
            lang, info = self.get_lang_by_type(test['ch'][1])
            if int(highest_quality) >= 720:
                sources.append(
                    {'source': "pvpzwa3r", 'quality': 'HD', 'language': lang, 'url': url, 'info': info, 'direct': True,
                     'debridonly': False})
            else:
                sources.append(
                    {'source': "pvpzwa3r", 'quality': 'SD', 'language': lang, 'url': url, 'info': info, 'direct': True,
                     'debridonly': False})
            return sources
        except:
            return sources

    def resolve(self, url):
        return url


from itertools import cycle


def do_xor(key, str):
    key = ''.join(key.split()[::-1]).decode('hex')
    return ''.join([chr(ord(a) ^ ord(b)) for a,b in zip(str, cycle(key))])