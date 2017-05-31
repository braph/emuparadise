#!/usr/bin/python3

# emu_dl.py - download files from emuparadise.me
# Copyright (C) 2017 Benjamin Abendroth
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" download files from emuparadise.me """

import io
import os
import sys
import json
import requests
import subprocess
from urllib.parse import urlsplit
from lxml import etree

from selenium import webdriver


class EmuDownloadUrlRetriever:
    """
        Retrieve direct download links for Game-URL.
        Note that you have to set the referer to http://www.emuparadise.me
        for the download to work!
    """

    def __init__(self, cookie_file=None):
        """ set cookie_file to type captcha only once """
        self.cookie_file = cookie_file
        self.cookies = None
        self._load_cookies()

    def _load_cookies(self):
        """ Restore cookies from cookies file """
        if not self.cookie_file:
            return

        try:
            with open(self.cookie_file, 'r') as f:
                try:
                    self.cookies = json.load(f)
                except Exception as e:
                    print("Error while cookies from file:", e)
        except FileNotFoundError:
            pass

    def _save_cookies(self):
        if not self.cookie_file:
            return

        try:
            with open(self.cookie_file, 'w') as f:
                json.dump(self.cookies, f)
        except Exception as e:
            print("Error while saving cookies to file:", e)

    def _solve_captcha(self, url):
        driver = webdriver.PhantomJS(service_log_path=os.devnull)
        driver.get(url)

        captcha_in = driver.find_element_by_xpath('//input[@id = "adcopy_response"]')

        try:
            import PIL.Image
            full_screenshot_bytes = driver.get_screenshot_as_png()
            full_screenshot_image = PIL.Image.open(io.BytesIO(full_screenshot_bytes))

            try:
                captcha_div = driver.find_element_by_xpath('//div[@id="captchadiv"]')
                captcha_image = full_screenshot_image.crop((
                    captcha_div.location['x'],
                    captcha_div.location['y'],
                    captcha_div.location['x'] + 400,
                    captcha_div.location['y'] + 400,
                ))
                captcha_image.show()
            except: # full screenshoft as fallback
                full_screenshot_image.show()

            captcha = input('captcha: ')
        except ImportError:
            import tempfile
            import subprocess
            with tempfile.NamedTemporaryFile() as tmp:
                driver.get_screenshot_as_file(tmp.name)
                p = subprocess.Popen(['feh', tmp.name])
                captcha = input('captcha: ')
                p.terminate()

        captcha_in.send_keys(captcha + "\n")

        self.cookies = { c['name']: c['value'] for c in driver.get_cookies() }

    def _return_download_link(self, url):
        response = requests.get(url, cookies=self.cookies)
        tree = etree.parse(io.StringIO(response.text), etree.HTMLParser())
        href = tree.xpath('//a[contains(@href, "get-download")]')[0].attrib['href']
        url_infos = urlsplit(url)
        return '%s://%s%s' % (url_infos.scheme, url_infos.netloc, href)

    def get_download_url(self, url):
        if not url.endswith('-download'):
            url += '-download'

        if not self.cookies:
            self._solve_captcha(url)

        for tries in range(3):
            try:
                direct_link = self._return_download_link(url)
                self._save_cookies() # success! it makes sense to store the cookies now
                return direct_link
            except Exception as e:
                print("Could not find direct-url: ", str(e))
                self._solve_captcha(url)

        raise Exception('Could not get link. Wrong captcha?')


class EmuDownload:
    def __init__(self, cookie_file=None):
        self.url_retriever = EmuDownloadUrlRetriever(
            cookie_file=cookie_file
        )

    def download(self, url):
        direct_url = self.url_retriever.get_download_url(url)

        url_infos = urlsplit(url)
        referer = '%s://%s' % (url_infos.scheme, url_infos.netloc)

        subprocess.run(['wget', '-c', '--content-disposition', '--referer', referer, direct_url])


if __name__ == '__main__':
    import os
    import argparse

    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('link',
                      help='Specify emuparadise game url to downlad',
                      nargs='*'
                      )
    argp.add_argument('--file',
                      help='Read links from file (specify »-« for STDIN)'
                      )
    group = argp.add_argument_group('advanced options')
    group.add_argument('--cookie-file',
                      default=os.path.expandvars('/tmp/emuparadise-$USER.cookie'),
                      help='Specify the cookie file'
                      )

    args = argp.parse_args()

    emu_download = EmuDownload(cookie_file=args.cookie_file)

    for link in args.link:
        emu_download.download(link)

    if args.file:
        if args.file == '-':
            for link in sys.stdin:
                emu_download.download(link.strip())
        else:
            with open(args.file, 'r') as f:
                for link in f:
                    emu_download.download(link.strip())

