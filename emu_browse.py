#!/usr/bin/env python3

# emu_browse.py - search/download games on emuparadise.me
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

""" Command line interface for emuparadise.me """

import os
import sys
import json
import argparse
import requests
from lxml import etree
from io import StringIO
from string import Template
from urllib.parse import quote as uri_escape

from collections import namedtuple

from emu_dl import EmuDownload

EmuFilter = namedtuple('EmuFilter', ('api_key', 'cmd_option', 'human_readable'))
EmuFilterValue = namedtuple('EmuFilterValue', ('value', 'human_readable'))

EMU_FILTERS = (
    EmuFilter('safety_ratings', 'safety', 'Safety Rating'),
    EmuFilter('gsysid', 'system', 'System Platform'),
    EmuFilter('regions', 'region', 'Regions'),
    EmuFilter('letter', 'letter', 'Start letter'),
    EmuFilter('genres', 'genre', 'Genre')
)

EMU_FILTER_VALUES = {ef.api_key: [] for ef in EMU_FILTERS}


# === Functions === #

def get_as_etree(url):
    response = requests.get(url)
    parser = etree.HTMLParser()
    return etree.parse(StringIO(response.text), parser)


def load_filter_values():
    try:
        with open(args.cache_file, 'r') as f:
            for api_key, filter_values in json.load(f).items():
                for filter_value in filter_values:
                    EMU_FILTER_VALUES[api_key].append(EmuFilterValue(*filter_value))
        return
    except FileNotFoundError:
        pass

    tree = get_as_etree('%s/roms/gamebrowser.php' % args.base)
    for t_input in tree.xpath('//input'):
        if 'name' not in t_input.attrib:
            continue

        try:
            t_label = t_input.getnext()
            if t_label.tag != 'label':
                continue
        except:
            continue

        label_for = t_label.attrib['for']

        for emu_filter in EMU_FILTERS:
            if t_input.attrib['name'].startswith(emu_filter.api_key):
                emu_filter_value = EmuFilterValue(
                    t_input.attrib['value'],
                    t_label.text
                )

                EMU_FILTER_VALUES[emu_filter.api_key].append(emu_filter_value)

    try:
        with open(args.cache_file, 'w') as f:
            json.dump(EMU_FILTER_VALUES, f)
    except Exception as e:
        print(e)


def lookup_filter_value(api_key, value):
    value = value.lower()

    if api_key == 'letter':
        if value.isdigit or value.isalpha():
            return '%s_letter' % value.upper()

    for emu_value in EMU_FILTER_VALUES[api_key]:
        if ('%s_%s' % (api_key, value)).lower() == emu_value.value.lower():
            return emu_value.value
        elif value.lower() == emu_value.value.lower():
            return emu_value.value

        # value is passed as human readable format
        elif emu_value.human_readable.lower() == value.lower():
            return emu_value.value

    raise Exception('Invalid filter option %s for filter %s' % (value, api_key))


def get_gamebrowser_results(url):
    next_url = '%s&page=1' % url

    while next_url:
        response = requests.get(next_url)

        if response.url.endswith('gamebrowser.php'):
            return # we have been redirected -> no results

        #debug_file = open('/tmp/dump.html', 'w')
        #debug_file.write(response.text)
        #debug_file.close()

        tree = etree.parse(StringIO(response.text), etree.HTMLParser())

        for row in tree.xpath('//table[@class="advance-search-results"]/tr'):
            try:
                td_game, td_system = row.xpath('td')
            except:
                continue

            system = td_system.text

            anchor = td_game.xpath('a')[0]
            rating = anchor.attrib['title'].replace('Game Rating: ', '')
            href = anchor.attrib['href']
            title = anchor.text

            if title:
                yield {
                    'title': title,
                    'system': system,
                    'rating': rating,
                    'url': args.base + href
                }
            else:
                pass # FIXME: could not extract title here, happens seldom
                #print("skipping")

        next_url = None
        for anchor in tree.xpath('//a'):
            if anchor.text is not None and anchor.text.startswith('Next Page'):
                next_url = args.base + anchor.attrib['href']


def limit_by_search(results):
    for game_title in results:
        if args.title in game_title['title'].lower():
            yield game_title


# === Action implementations === "
def do_help_filter():
    found_filter = False

    for emu_filter in EMU_FILTERS:
        if emu_filter.cmd_option == args.help_filter.lower():
            found_filter = True
            break

    if not found_filter:
        print('Filter not found')
        sys.exit(1)

    print('%s: --%s (internal api_key: %s)' % (
        emu_filter.human_readable,
        emu_filter.cmd_option,
        emu_filter.api_key
    ))

    if emu_filter.api_key == 'letter':
        print("\t0-9, A-Z")
    else:
        for emu_value in EMU_FILTER_VALUES[emu_filter.api_key]:
            print("\t% -30s%s" % (emu_value.value, emu_value.human_readable))


def do_list():
    argd = vars(args)

    request_url = '%s/roms/gamebrowser.php?sort=%s_%s&per_page=%s' % (
        args.base,
        args.sort,
        args.reverse,
        2000
    )

    for emu_filter in EMU_FILTERS:
        if argd[emu_filter.api_key]:
            for value in argd[emu_filter.api_key]:
                request_url += '&%s[]=%s' % (
                    emu_filter.api_key,
                    uri_escape(lookup_filter_value(emu_filter.api_key, value))
                )

    results = get_gamebrowser_results(request_url)

    if args.title:
        results = limit_by_search(results)

    if args.download:
        download = EmuDownload(args.cookie_file)
        for title_dict in results:
            if args.download_dir:
                pwd = os.path.abspath('.')
                try:
                    dest_dir = args.download_dir.substitute(**title_dict)
                    os.makedirs(dest_dir, exist_ok=True)
                    os.chdir(dest_dir)
                    download.download(title_dict['url'])
                finally:
                    os.chdir(pwd)
            else:
                download.download(title_dict['url'])
    else:
        for title_dict in results:
            print(args.format.substitute(**title_dict))


if __name__ == '__main__':

    # === Argument Parsing === #
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('--base-url',
                      metavar='BASE_URL',
                      default='http://www.emuparadise.me',
                      type=lambda u: u if u.startswith('http') else 'http://%s' % u,
                      help='Specify emuparadise base URL',
                      dest='base'
                      )

    # === Option listing ===  #
    argp.add_argument('--help-filter',
                      help='List all available options for filter',
                      choices=[ef.cmd_option for ef in EMU_FILTERS],
                      )

    # === Game listing === #
    group = argp.add_argument_group('filter options')
    group.add_argument('--title',
                      help='Search in game titles',
                      #nargs='?',
                      type=str.lower
                      )

    for emu_filter in EMU_FILTERS:
        group.add_argument(
            ('--%s' % emu_filter.cmd_option),
            help=('Filter by %s (can be specified multiple times)' % emu_filter.human_readable),
            dest=emu_filter.api_key,
            metavar=emu_filter.cmd_option.upper(),
            action='append'
        )

    # === Listing options ===
    group = argp.add_argument_group('list options')
    group.add_argument('--format',
                      help='Specify output format (available variables: $title, $system, $rating, $url)',
                      default='$title $system [$rating] $url',
                      type=Template
                      )
    group.add_argument('--sort',
                      help='Sort results',
                      choices=('name', 'rating', 'downloads'),
                      default='name'
                      )
    group.add_argument('--reverse',
                      help='Reverse sorting',
                      action='store_const',
                      const='Descending',
                      default='Ascending'
                      )

    group.add_argument('--download',
                      help='Download found titles',
                      action='store_true'
                      )
    group.add_argument('--download-dir',
                      help='Specify output directory',
                      type=Template
                      )

    # === Advanced Options ===
    group = argp.add_argument_group('advanced options')
    group.add_argument('--cookie-file',
                      default=os.path.expandvars('/tmp/emuparadise-$USER.cookie'),
                      help='Specify the cookie file'
                      )
    group.add_argument('--cache-file',
                      default=os.path.expandvars('/tmp/emuparadise-$USER.cache'),
                      help='This file is used to store the available filter options'
                      )
    group.add_argument('--purge',
                      help='Purge cache file on startup',
                      action='store_true'
                      )

    args = argp.parse_args()

    if args.purge:
        try: os.remove(args.cache_file)
        except FileNotFoundError: pass
        try: os.remove(args.cookie_file)
        except FileNotFoundError: pass

    load_filter_values()

    if args.help_filter:
        do_help_filter()
    else:
        do_list()
