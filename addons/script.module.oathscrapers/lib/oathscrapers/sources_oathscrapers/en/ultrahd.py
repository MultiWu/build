# -*- coding: utf-8 -*-

import re,urllib,urlparse
from oathscrapers.modules import client
from oathscrapers.modules import debrid
from oathscrapers.modules import dom_parser2
from oathscrapers.modules import source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['ultrahdindir.com']
        self.base_link = 'https://ultrahdindir.com'
        self.post_link = '/index.php?do=search'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url == None:
                return sources
            if debrid.status() is False:
                raise Exception()
            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['title'].replace(':', '').lower()
            year = data['year']
            query = '%s %s' % (data['title'], data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            url = urlparse.urljoin(self.base_link, self.post_link)
            post = 'do=search&subaction=search&search_start=0&full_search=0&result_from=1&story=%s' % urllib.quote_plus(query)
            r = client.request(url, post=post)
            r = client.parseDOM(r, 'div', attrs={'class': 'box-out margin'})
            r = [(dom_parser2.parse_dom(i, 'div', attrs={'class': 'news-title'})) for i in r if data['imdb'] in i]
            r = [(dom_parser2.parse_dom(i[0], 'a', req='href')) for i in r if i]
            r = [(i[0].attrs['href'], i[0].content) for i in r if i]
            hostDict = hostprDict + hostDict
            for item in r:
                try:
                    name = item[0]
                    s = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', name)
                    s = s[0] if s else '0'
                    data = client.request(item[0])
                    data = dom_parser2.parse_dom(data, 'div', attrs={'id': 'r-content'})
                    data = re.findall('\s*<b><a href="(.+?)".+?</a></b>', data[0].content, re.DOTALL)
                    for url in data:
                        url = client.replaceHTMLCodes(url)
                        url = url.encode('utf-8')

                        if 'turbobit' not in url:
                            continue
                        valid, host = source_utils.is_host_valid(url, hostDict)
                        if not valid:
                            continue
                        try:
                            qual = client.request(url)
                            quals = re.findall('span class="file-title" id="file-title">(.+?)</span', qual)
                            for quals in quals:
                                quality = source_utils.check_sd_url(quals)
                            info = []
                            if '3D' in name or '.3D.' in quals:
                                info.append('3D'); quality = '1080p'
                            info = ' | '.join(info)
                            sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': True, 'debridonly': True})
                        except:
                            pass
                except:
                    pass
            return sources
        except:
            return sources


    def resolve(self, url):
        return url

