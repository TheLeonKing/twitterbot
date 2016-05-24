# A small tool to download the bot's direct messages and save them to a server.

import ConfigParser
import cPickle
import ftplib

from twython import Twython

config = ConfigParser.ConfigParser()
config.read('config.ini')

twython = Twython(
    config.get('twitter', 'appKey'),
    config.get('twitter', 'appSecret'),
    config.get('twitter', 'oAuthToken'),
    config.get('twitter', 'oAuthSecret')
)

session = ftplib.FTP(
    config.get('ftp', 'host')
    config.get('ftp', 'user')
    config.get('ftp', 'pass')
)

botType = config.get('db', 'name')

# Save direct messages to pickle.
dms = twython.get_direct_messages()
fileName = 'dms_' + botType + '.pkl'
cPickle.dump(dms, open(fileName, 'wb'))

# Upload pickle to FTP server.
file = open(fileName, 'rb')
session.storbinary('STOR ' + fileName, file)
file.close()
session.quit()
