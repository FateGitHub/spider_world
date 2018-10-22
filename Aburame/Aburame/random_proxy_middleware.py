#!/usr/bin/env python 
# coding:utf-8
# @Time :9/17/18 11:09

import base64
from six.moves.urllib.request import getproxies, proxy_bypass
from six.moves.urllib.parse import unquote
import requests
try:
    from urllib2 import _parse_proxy
except ImportError:
    from urllib.request import _parse_proxy
from six.moves.urllib.parse import urlunparse

from scrapy.utils.httpobj import urlparse_cached
from scrapy.exceptions import NotConfigured
from scrapy.utils.python import to_bytes

from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from logging import getLogger

import time


class RandomProxyMiddleware(HttpProxyMiddleware):
    logger = getLogger("RandomProxyMiddleware")

    def __init__(self, auth_encoding='latin-1', host=None):
        super(RandomProxyMiddleware, self).__init__()
        self.auth_encoding = auth_encoding
        self.proxies = {}
        self.host = host
        for type, url in getproxies().items():
            self.proxies[type] = self._get_proxy(url, type)

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('HTTPPROXY_ENABLED'):
            raise NotConfigured
        auth_encoding = crawler.settings.get('HTTPPROXY_AUTH_ENCODING')
        host = crawler.settings.get('HOST')
        return cls(auth_encoding, host)

    def _basic_auth_header(self, username, password):
        user_pass = to_bytes(
            '%s:%s' % (unquote(username), unquote(password)),
            encoding=self.auth_encoding)
        return base64.b64encode(user_pass).strip()

    def _get_proxy(self, url, orig_type):
        proxy_type, user, password, hostport = _parse_proxy(url)
        proxy_url = urlunparse((proxy_type or orig_type, hostport, '', '', '', ''))

        if user:
            creds = self._basic_auth_header(user, password)
        else:
            creds = None

        return creds, proxy_url

    def process_request(self, request, spider):
        # ignore if proxy is already set
        request.meta['proxy'] = "your_ip_here"
        if 'proxy' in request.meta:
            if request.meta['proxy'] is None:
                return
            # extract credentials if present
            creds, proxy_url = self._get_proxy(request.meta['proxy'], '')
            request.meta['proxy'] = proxy_url
            if creds and not request.headers.get('Proxy-Authorization'):
                request.headers['Proxy-Authorization'] = b'Basic ' + creds
            return
        elif not self.proxies:
            return

        parsed = urlparse_cached(request)
        scheme = parsed.scheme

        # 'no_proxy' is only supported by http schemes
        if scheme in ('http', 'https') and proxy_bypass(parsed.hostname):
            return

        if scheme in self.proxies:
            self._set_proxy(request, scheme)

    def _set_proxy(self, request, scheme):
        creds, proxy = self.proxies[scheme]
        request.meta['proxy'] = proxy
        if creds:
            request.headers['Proxy-Authorization'] = b'Basic ' + creds
