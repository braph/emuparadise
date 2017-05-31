# emuparadise
commandline client for downloading games from emuparadise

```
usage: emu_browse.py [-h] [--base-url BASE_URL]
                     [--help-filter {safety,system,region,letter,genre}]
                     [--title TITLE] [--safety SAFETY] [--system SYSTEM]
                     [--region REGION] [--letter LETTER] [--genre GENRE]
                     [--format FORMAT] [--sort {name,rating,downloads}]
                     [--reverse] [--download] [--download-dir DOWNLOAD_DIR]
                     [--cookie-file COOKIE_FILE] [--cache-file CACHE_FILE]
                     [--purge]

Command line interface for emuparadise.me

optional arguments:
  -h, --help            show this help message and exit
  --base-url BASE_URL   Specify emuparadise base URL
  --help-filter {safety,system,region,letter,genre}
                        List all available options for filter

filter options:
  --title TITLE         Search in game titles
  --safety SAFETY       Filter by Safety Rating (can be specified multiple
                        times)
  --system SYSTEM       Filter by System Platform (can be specified multiple
                        times)
  --region REGION       Filter by Regions (can be specified multiple times)
  --letter LETTER       Filter by Start letter (can be specified multiple
                        times)
  --genre GENRE         Filter by Genre (can be specified multiple times)

list options:
  --format FORMAT       Specify output format (available variables: $title,
                        $system, $rating, $url)
  --sort {name,rating,downloads}
                        Sort results
  --reverse             Reverse sorting
  --download            Download found titles
  --download-dir DOWNLOAD_DIR
                        Specify output directory

advanced options:
  --cookie-file COOKIE_FILE
                        Specify the cookie file
  --cache-file CACHE_FILE
                        This file is used to store the available filter
                        options
  --purge               Purge cache file on startup
```
