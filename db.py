'''
Contains all functions related to database access and management.
'''

import ConfigParser
import logging
import MySQLdb
import sys


# Read the config file.
config = ConfigParser.ConfigParser()
config.read('config.ini')

# Set up the error file.
logging.basicConfig(filename='errors.log',
                    level=logging.WARNING
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filemode='w')


# Set the handle and database configuration.
myHandle = config.get('bot', 'handle')
dbC = {
    'host': config.get('db', 'host'),
    'port': int(config.get('db', 'port')),
    'user': config.get('db', 'user'),
    'pass': config.get('db', 'pass'),
    'name': config.get('db', 'name')
}


def connect(db):
    return MySQLdb.connect(dbC['host'], dbC['user'], dbC['pass'], db, port=dbC['port'])

def executeQuery(query, values=(), db=dbC['name'], output=False):
    try:
        db = connect(db)
        cursor = db.cursor()
        cursor.execute(query, values)
        if output: return cursor.fetchall()
    except Exception as e:
        logging.warning('DBX ERROR executeQuery (query=' + query + '):' + str(e))

def createDb(db):
    con = MySQLdb.connect(dbC['host'], dbC['user'], dbC['pass'], port=dbC['port'])
    cursor = con.cursor()
    sql = 'CREATE DATABASE IF NOT EXISTS %s;' % db
    cursor.execute(sql)
    
def createTable(db, tableName, colName='id', colType='INT', specifier='AUTO_INCREMENT'):
    query = ('CREATE TABLE IF NOT EXISTS %s'
    ' (%s %s PRIMARY KEY %s)'
    ' ENGINE=MyISAM DEFAULT CHARSET=latin1;') % (tableName, colName, colType, specifier)
    executeQuery(query)
    
def addColumn(db, tableName, colName, dType, keywords=''):
    query = 'ALTER TABLE `%s` ADD %s %s %s;' % (tableName, colName, dType, keywords)
    executeQuery(query)

def fetchTweets():
    ' Fetches all tweets the bot has tweeted. '
    query = 'SELECT * FROM tweets'
    return executeQuery(query, output=True)

def init():
	' Initializes the database. '

	# Create Twitter Bot database.
	createDb(dbC['name'])

	# Create tweets table.
	createTable(dbC['name'], 'tweets')
	addColumn(dbC['name'], 'tweets', 'tweet', 'VARCHAR(256)')
	addColumn(dbC['name'], 'tweets', 'url', 'VARCHAR(256)')
	addColumn(dbC['name'], 'tweets', 'bitly', 'VARCHAR(256)')
	addColumn(dbC['name'], 'tweets', 'pic', 'VARCHAR(256)')
	addColumn(dbC['name'], 'tweets', 'timestamp', 'TIMESTAMP', 'ON UPDATE CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP')

	# Create retweets table.
	createTable(dbC['name'], 'retweets')
	addColumn(dbC['name'], 'retweets', 'tweet_id', 'BIGINT(255)', 'UNSIGNED')
	addColumn(dbC['name'], 'retweets', 'tweet_text', 'VARCHAR(256)')
	addColumn(dbC['name'], 'retweets', 'user', 'VARCHAR(64)')
	addColumn(dbC['name'], 'retweets', 'followers', 'INT(12)')
	addColumn(dbC['name'], 'retweets', 'retweets', 'INT(12)', 'UNSIGNED')
	addColumn(dbC['name'], 'retweets', 'timestamp', 'TIMESTAMP', 'ON UPDATE CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP')

	# Create follows table.
	createTable(dbC['name'], 'follows')
	addColumn(dbC['name'], 'follows', 'user_id', 'BIGINT(255)', 'UNSIGNED')
	addColumn(dbC['name'], 'follows', 'user_handle', 'VARCHAR(64)')
	addColumn(dbC['name'], 'follows', 'followers', 'INT(12)')
	addColumn(dbC['name'], 'follows', 'tweet_text', 'VARCHAR(256)')
	addColumn(dbC['name'], 'follows', 'source', 'VARCHAR(64)')
	addColumn(dbC['name'], 'follows', 'timestamp', 'TIMESTAMP', 'ON UPDATE CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP')

	# Create followers table.
	createTable(dbC['name'], 'followers')
	addColumn(dbC['name'], 'followers', 'user_id', 'BIGINT(255)', 'UNSIGNED')
	addColumn(dbC['name'], 'followers', 'user_handle', 'VARCHAR(64)')
	addColumn(dbC['name'], 'followers', 'followers', 'INT(12)')
	addColumn(dbC['name'], 'followers', 'timestamp', 'TIMESTAMP', 'ON UPDATE CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP')

	# Create keywords table.
	createTable(dbC['name'], 'keywords', colName='keyword', colType='VARCHAR(64)', specifier='')

	# Create accounts table.
	createTable(dbC['name'], 'accounts', colName='account', colType='VARCHAR(64)', specifier='')

	# Create tweet_probs table.
	createTable(dbC['name'], 'tweet_probs', colName='tweet_type', colType='VARCHAR(64)', specifier='')
	addColumn(dbC['name'], 'tweet_probs', 'tweet_prob', 'DOUBLE(25, 22)', 'DEFAULT 0')

	# Create follow_probs table.
	createTable(dbC['name'], 'follow_probs', colName='follow_type', colType='VARCHAR(64)', specifier='')
	addColumn(dbC['name'], 'follow_probs', 'follow_prob', 'DOUBLE(25, 22)', 'DEFAULT 0')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        init()

