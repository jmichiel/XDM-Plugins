'''
Created on 16-nov.-2013

@author: unlord
'''
from xdm.plugins import Indexer, log, Download
from lib import requests
from bs4 import BeautifulSoup
from urlparse import parse_qs
import re
from base64 import b32decode, b16encode



class PublicHD(Indexer):
    version = "0.1"
    identifier = "be.unlord.publichd"
    _config = {'enabled': True,
               'comment_on_download': False,
               'verify_ssl_certificate': True,
               'use_torrentcache' : False,
               'torrentcache_link' : 'http://torrage.com/torrent/%s.torrent'
               }
    config_meta = {'use_torrentcache': {'human': 'Use torrent cache links',
                                        'desc': 'Instead of using the links to the torrent files PublicHD gives, build links to cached torrent files on a torrent caching site such as Torrage.com'},
                   'torrentcache_link': {'human': 'Torrent Link format',
                                         'desc': 'use %%s to indicate where the torrent ID is to be filled in. e.g. http://torrage.com/torrent/%s.torrent'}}

    types = ['de.lad1337.movies', 'de.lad1337.torrent']
    
    _seachUrl = 'https://publichd.se/index.php'


    def searchForElement(self, element):
        downloads = []
        category = str(self._getCategory(element))
        if category != 'Movies':
            log("Can only search for movies on PublicHD!")
            return []
        terms = element.getSearchTerms()
        log.debug('terms: %s' % terms)
        for term in terms:
            payload = {
                'page':'torrents',
                'search': term,
                'active': 1,
            }
            response = requests.get(self._seachUrl, params=payload, verify=self.c.verify_ssl_certificate)
            log("PublicHD final search for term %s url %s" % (term, response.url))

            soup = BeautifulSoup(response.text)

            entries = soup.find('table', attrs = {'id': 'torrbg'}).find_all('tr')

            for result in entries:
                info_url = result.find(href = re.compile('torrent-details'))
                magnet = result.find(href = re.compile('magnet:'))
                download = result.find(href = re.compile(r'\.torrent$'))

                if info_url and download and magnet:
                    log("%s found on PublicHD: %s" % (element.type, info_url.string))
                    dl_url = download['href']
                    if self.c.use_torrentcache:
                        dl_url = self._decodeMagnet(magnet['href'])
                        log.debug('PublicHD: magnet link \'%s\' translated to url \'%s\'' % (magnet['href'], dl_url))

                    size = result.find_all('td')[7].find('b').string
                    info = parse_qs(info_url['href'])

                    d = Download()
                    d.url = dl_url
                    d.name = info_url.string
                    d.element = element
                    d.size = self._decodeSize(size)
                    d.external_id = info['id'][0]
                    d.type = 'de.lad1337.torrent'
                    downloads.append(d)
        return downloads


    def _decodeSize(self, sizestr):
        match = re.search(r'(\d+\.\d+) ([TGMK])B', sizestr)
        if match:
            size = float(match.group(1))
            if match.group(2) == "T":
                size = size * 1024 * 1024 * 1024
            elif match.group(2) == "G":
                size = size * 1024 * 1024
            elif match.group(2) == "M":
                size = size * 1024
            return int(size * 1024) #result in bytes
        else:
            log.error("Decoding torrent size from %s failed!" % size)
        return 0
    
    def _decodeMagnet(self, magnet_link):
        magnet_hash = re.findall(r'urn:btih:([\w]{32,40})', magnet_link)[0].upper()

        # Convert base 32 to hex
        if len(magnet_hash) == 32:
            magnet_hash = b16encode(b32decode(magnet_hash))
        url = self.c.torrentcache_link % magnet_hash
        return url

    def commentOnDownload(self, download):
        return True
