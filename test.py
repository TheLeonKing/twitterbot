import bitly_api
import db
import ConfigParser
import datetime
import flickrapi
import gnp
import logging
import json
import numpy as np
import operator
import probs
import random
import re
import related
import requests
import sched
import sys
import textwrap
import time
import urllib

from time import sleep
from StringIO import StringIO
from sys import stdout
from twython import Twython


# Read the config file.
config = ConfigParser.ConfigParser()
config.read('config.ini')

# Set up the error file.
logging.basicConfig(filename='errors.log', level=logging.WARNING)

# Set the bot's handle.
myHandle = config.get('bot', 'handle')

# Set up the Alchemy, Bitly, Flickr and Twitter API.
alchemyApiKey = config.get('alchemy', 'apiKey')
bitlyConn = bitly_api.Connection(config.get('bitly', 'apiKey'), config.get('bitly', 'accessToken'))
flickr = flickrapi.FlickrAPI(config.get('flickr', 'key'), config.get('flickr', 'secret'), format='parsed-json')
twython = Twython(
    config.get('twitter', 'appKey'),
    config.get('twitter', 'appSecret'),
    config.get('twitter', 'oAuthToken'),
    config.get('twitter', 'oAuthSecret'),
    client_args =   {
                        'proxies': {
                            'http' : config.get('proxies', 'http'),
                            'https': config.get('proxies', 'https')
                        }
                    }
)


