# coding=utf-8
''' The Twitter bot script that constantly runs. '''

import bitly_api
import db
import ConfigParser
import datetime
import feedparser
import flickrapi
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
logging.basicConfig(filename='errors.log',
                    level=logging.WARNING,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filemode='w')

# Set the bot's handle and find out if bot is in trending mode.
myHandle = config.get('bot', 'handle')
trending = True if config.get('bot', 'trending') == 'True' else False

# Set up the Alchemy, Bitly, Flickr and Twitter API.
alchemyApiKey = config.get('alchemy', 'apiKey')
bitlyConn = bitly_api.Connection(config.get('bitly', 'apiKey'), config.get('bitly', 'accessToken'))
flickr = flickrapi.FlickrAPI(config.get('flickr', 'key'), config.get('flickr', 'secret'), format='parsed-json')
twython = Twython(
    config.get('twitter', 'appKey'),
    config.get('twitter', 'appSecret'),
    config.get('twitter', 'oAuthToken'),
    config.get('twitter', 'oAuthSecret')
)

# Set up the bad words list.
badWords = set(line.strip('\n') for line in open('bad_words.txt'))

# Initialize related keywords + accounts and tweet + follow probabilities.
keywords = related.fetchRelated('keywords')
relatedAccounts = related.fetchRelated('accounts')
tweetProbs = probs.fetchProbs('tweet')
followProbs = probs.fetchProbs('follow')


def bitly(url):
    ' Takes an URL, returns its shortened bit.ly URL. '
    shorten = bitlyConn.shorten(url)
    return shorten['url']

def rKeyword():
    ' Returns a random keyword. '
    return random.choice(keywords)

def relatedAcc():
    ' Returns a random related account. '
    return random.choice(relatedAccounts)

def insertTweet(tweet, url=None, bitly=None, pic=None):
    ' Inserts a tweet into the database. '
    query = 'INSERT INTO tweets (tweet, url, bitly, pic) VALUES (%s, %s, %s, %s);'
    db.executeQuery(query, (tweet, url, bitly, pic))
    
def insertRetweet(tweet_id, tweet_text, user, followers, retweets):
    ' Inserts a retweet into the database. '
    query = 'INSERT INTO retweets (tweet_id, tweet_text, user, followers, retweets) VALUES (%s, %s, %s, %s, %s);'
    db.executeQuery(query, (tweet_id, tweet_text, user, followers, retweets))

def insertFollow(uId, uHandle, followers, tweet, source):
    ' Inserts a follow interaction into the database. '
    query = 'INSERT INTO follows (user_id, user_handle, followers, tweet_text, source) VALUES (%s, %s, %s, %s, %s);'
    db.executeQuery(query, (uId, uHandle, followers, tweet, source))

def insertFollower(uId, uHandle, followers):
    ' Inserts a follow interaction into the database. '
    query = 'INSERT INTO followers (user_id, user_handle, followers) VALUES (%s, %s, %s);'
    db.executeQuery(query, (uId, uHandle, followers))
    
def tweet(text, url=None, pic=None, hashtag=None):
    ' Directly posts a (general) tweet. '
    logging.warning('debug1')
    tweet, url_bitly = generateTweet(text, url, hashtag)
    
    # If the tweet has a picture, upload it and post a media tweet.
    if pic:
        photo = (StringIO(urllib.urlopen(url).read()))
        logging.warning('debug3')
        response = twython.upload_media(media=photo)
        logging.warning('debug4')
        tweet = twython.update_status(status=tweet, media_ids=[response['media_id']])['text']
        logging.warning('BOT TWREQ tweet1')
    # If this tweet doesn't have a picture, post a general tweet.
    else:
        twython.update_status(status=tweet)
        logging.warning('BOT TWREQ tweet2')
    
    # Insert Tweet into database.
    insertTweet(tweet, url=url, bitly=url_bitly, pic=pic)

    return tweet

def generateTweet(text, url, hashtag):
    """ Generates a tweet's text. """
    
    logging.warning('debug2.1')
    # Shorten URL and set hashtag (if they are provided).
    url_bitly = bitly(url) if url else ''
    hashtag = '#' + re.sub('[^A-Za-z0-9]+', '',  hashtag) if hashtag else ''
    
    logging.warning('debug2.2')
    # Max text length is 140 - 25 (link length) - length hashtag - two whitespaces.
    textlength = 140 - 25 - len(hashtag) - 2
    
    logging.warning('debug2.3')
    # Split at space before `textlength` characters, return full tweet.
    try:
        text = unicode(text, 'utf-8', 'replace')
    except:
        text = text.encode('utf-8', 'ignore')

    logging.warning('debug2.4')
    text = textwrap.wrap(text, textlength)[0]

    logging.warning('debug2.5')
    tweet = ' '.join([text, hashtag, url_bitly])
    
    logging.warning('debug2.6')
    return (tweet, url_bitly) if len(tweet) <= 140 else (tweet[0:140], url_bilty)


def exists(col, val, table='tweets'):
    ''' Checks whether a column-value pair exists, e.g.
        to check if a picture has already been tweeted. '''
    noOfResults = len(db.executeQuery('SELECT * FROM ' + table + ' WHERE ' + str(col) + ' = "' + str(val) + '"', output=True))
    return True if (noOfResults > 0) else False


################
### TWEETING ###
################

def tweetNews(keyword=rKeyword()):
    ' Tweets a news article (based on a keyword). '

    # Fetch news articles matching our keyword.
    results = feedparser.parse('https://news.google.com/news/section?ned=us&output=rss&q=' + keyword)
    
    # Tweet the first news article the bot hasn't tweeted about yet.
    for entry in results.entries:
        try:
            title = unicode(entry.title, 'utf-8', 'replace')
            link = unicode(entry.link.split('url=', 1)[1])
        except:
            title = (entry.title).encode('utf-8', 'ignore')
            link = (entry.link.split('url=', 1)[1]).encode('utf-8', 'ignore')
        

        try:
            title = title.split(' -')
            del title[-1]
            title = ' '.join(title)
        except:
            pass

        if not exists('url', link):
            print '\nTweeted (news):', tweet(title, url=link, hashtag=keyword)
            return None

def tweetPicture(keyword=rKeyword(), page=1):
    ' Tweet a picture (based on a keyword). '
    
    # Find the first 100 results matching our keyword.
    results = flickr.photos.search(text=keyword, safe_search=1, content_type=1, page=1)
    
    logging.warning('debug0.1')
    # Loop through the results until we find a photo we haven't tweeted yet.
    for pic in results['photos']['photo']:

        logging.warning('debug0.2')
        pic['id'] = pic['id'].encode('utf-8', 'replace')
        if not exists('pic', pic['id']):
            
            logging.warning('debug0.3')
            try:
                pic['title'] = unicode(pic['title'], 'utf-8', 'replace')
                pic['url'] = unicode(flickr.photos.getSizes(photo_id=pic['id'])['sizes']['size'][6]['source'], 'utf-8', 'replace')
            except:
                pic['title'] = pic['title'].encode('utf-8', 'ignore')
                pic['url'] = flickr.photos.getSizes(photo_id=pic['id'])['sizes']['size'][6]['source'].encode('utf-8', 'ignore')
            
            logging.warning('debug0.4')
            print '\nTweeted (picture):', tweet(pic['title'], url=pic['url'], pic=pic['id'], hashtag=keyword)
            return None
    
    # If the loop ended, we've tweeted all pictures already --> recursively call the next page.
    findPicture(keyword, page=page+1)

def retweet(keyword=rKeyword()):
    '''
    Retweets the first tweet that matches the given keyword,
    only if it is (1) longer than 70 chars; (2) written in
    English; (3) positive; (4) not offensive (no swear words);
    and (5) if the bot hasn't already retweeted it.
    '''
    
    # Find the results matching the keyword.
    results = twython.search(q=keyword, lang='en')['statuses']
    logging.warning('BOT TWREQ retweet1')
    
    # Calculate a score for each tweet, based on the persons no. of followers and the tweet's no. of retweets.
    for tweet in results:
        tweet['score'] = 0
        if (tweet['user']['followers_count'] > 0): tweet['score'] += np.log(tweet['user']['followers_count']) 
        if (tweet['retweet_count'] > 0): tweet['score'] += np.log(tweet['retweet_count'])
    
    # Sort results, with the highest score first.
    results = sorted(results, key=lambda k: k['score'], reverse=True)
    
    for tweet in results:
        # Correctly encode the tweet and screen name.
        try:
            tweet['text'] = unicode(tweet['text'], 'utf-8', 'replace')
            tweet['user']['screen_name'] = unicode(tweet['user']['screen_name'], 'utf-8', 'replace')
        except:
            tweet['text'] = tweet['text'].encode('utf-8', 'ignore')
            tweet['user']['screen_name'] = tweet['user']['screen_name'].encode('utf-8', 'ignore')
        
        # Retweet the first tweet that satisfies all the requirements.
        if longTweet(tweet) and englishTweet(tweet) and positiveTweet(tweet) and notOffensive(tweet) and not exists('id', tweet['id'], 'retweets'):
            twython.retweet(id=tweet['id'])
            logging.warning('BOT TWREQ retweet2')
            insertRetweet(tweet['id'], tweet['text'], tweet['user']['screen_name'], tweet['user']['followers_count'], tweet['retweet_count'])
            print '\nRetweeted:', tweet['text']
            return None
    
    # If no suitable tweets were found, try again in 60 seconds.
    print "\nCouldn't find suitable tweets. Trying again in a minute..."
    sleep(60)
    return retweet(keyword)

def longTweet(tweet):
    ' Checks if a tweet is longer than 70 characters. '
    return len(tweet['text']) > 70

def englishTweet(tweet):
    ' Checks if a tweet is written in English. '
    return tweet['metadata']['iso_language_code'] == 'en'

def notOffensive(tweet):
    " Checks if a tweet doesn't contain bad words. "
    for word in re.findall(r"[A-Za-z]+|\S", tweet['text']):
        if word in badWords:
            return False
    return True

def positiveTweet(tweet, attempt=0):
    ''' Checks if a tweet is positive.
        Sentiment analysis performed using the Alchemy API. '''
    
    # Set up Alchemy API request.
    alchemyUrl = 'http://access.alchemyapi.com/calls/text/TextGetTextSentiment'
    parameters = {
        'apikey' : alchemyApiKey,
        'text' : tweet['text'],
        'outputMode' : 'json',
        'showSourceText' : 1
        }
    
    # Perform Alchemy API request. Return True if sentiment is positive (and False otherwise).
    try:
        results = requests.get(url=alchemyUrl, params=urllib.urlencode(parameters))
        response = results.json()
        return True if (response['docSentiment']['type'] == 'positive') else False

    # If Alchemy API request failed, try again after two seconds. Give up after more than 5 failed attempts.
    except Exception as e:
        print '\nError during sentiment analysis for tweet %s. Error: %s.' % (tweet['id'], e)
        logging.error('BOT ERROR positiveTweet ' + str(e))
        sleep(2)
        return True if (attempt > 5) else positiveTweet(tweet, attempt+1)


#################
### FOLLOWING ###
#################

def follow(uId, uHandle, followers, tweet=None, source=None):
    ' Follows a user and insert the follow interaction in the database. '
    uHandle = uHandle.encode('utf-8', 'replace')
    twython.create_friendship(user_id=uId)
    logging.warning('BOT TWREQ follow')
    insertFollow(uId, uHandle, followers, tweet, source)
    
    # Print feedback, based on whether the follow action was
    # based on a keyword or on a related account (source).
    if tweet: print '\nFollowed (keyword)', uHandle, '(', tweet, ')'
    elif source: print '\nFollowed (source)', uHandle, '(', source, ')'

def followKeyword(keyword=rKeyword()):
    ' Follows a user based on a keyword. '
    results = twython.search(q=keyword, lang='en', count=10)
    logging.warning('BOT TWREQ followKeyword')
    try:
        for tweet in results['statuses']:
            try:
                # Extract necessary information about tweet and user.
                uId = int(tweet['user']['id'])
                followers = tweet['user']['followers_count']

                try:
                    uHandle = unicode(tweet['user']['screen_name'], 'utf-8', 'replace')
                    tweet = unicode(tweet['text'], 'utf-8', 'replace')
                except:
                    uHandle = tweet['user']['screen_name'].encode('utf-8', 'replace')
                    tweet = tweet['text'].encode('utf-8', 'replace')
                
                # Follow user and insert follow interaction in database.
                follow(uId, uHandle, followers, tweet=tweet)
                return None
            except Exception as e:
                logging.error('BOT ERROR followKeyword1: ' + str(e))
    except Exception as e:
        logging.error('BOT ERROR followKeyword2: ' + str(e))

def followBack():
    '''
    Follows the first person who follows the
    bot, but is not followed back by the bot.
    '''
    followRelated(myHandle)

def followRelated(handle=relatedAcc()):
    '''
    Takes a Twitter handle (`handle`), or randomly
    chooses a related account's handle.
    Follows the first user who follows `handle`,
    but who is not yet followed by the bot.
    '''
    nextCursor = -1
    try:
        # While the followers list contains more users (Twitter API has max of 200 users per request).
        while(nextCursor):
            results = twython.get_followers_list(screen_name=handle, count=200, cursor=nextCursor)
            logging.warning('BOT TWREQ followRelated')
            
            # Follow the first user the bot is not already following.
            for user in results['users']:
                if not exists('user_id', user['id'], 'follows'):
                    follow(user['id'], user['screen_name'], user['followers_count'], source=handle)
                    return None
            nextCursor = results['next_cursor']
        
        # If the function hasn't returned yet, the bot is already following everyone from this account.
        print '\nAlready followed everyone from account', handle
        return False
    except Exception as e:
        logging.error('BOT ERROR followRelated: ' + str(e))

def unfollow():
    " Unfollows the oldest following user that doesn't follow the bot back. "
    
    # Find first user the bot is following.
    try:
        uId = db.executeQuery('SELECT user_id FROM follows WHERE active = 1 LIMIT 1', output=True)[0][0]
    except Exception as e:
        print "\nCouldn't find any suitable users to unfollow."
        return None
    
    # If user is following the bot, set active = 2 to prevent him from being unfollowed.
    if not exists('user_id', uId, 'followers'):
        db.executeQuery('UPDATE follows SET active = 2 WHERE user_id = %s', (uId,))
        return unfollow()
    
    # If user is not following the bot, unfollow him.
    try:
        twython.destroy_friendship(user_id=uId)
        print '\nUnfollowed user with ID ' + str(uId)
    except Exception as e:
        logging.error('BOT ERROR unfollow: ' + str(e))
    
    # Set active = 0 to indicate unfollow.
    db.executeQuery('UPDATE follows SET active = 0 WHERE user_id = %s', (uId,))

def updateFollowers():
    ' Updates the database of people who follow the bot. '
    nextCursor = -1
    try:
        # While the followers list contains more users (Twitter API has max of 200 users per request).
        while(nextCursor):
            results = twython.get_followers_list(screen_name=myHandle, count=200, cursor=nextCursor)
            logging.warning('BOT TWREQ updateFollowers')
            
            # Only insert a user if (s)he is not already in the database.
            for user in results['users']:
                if not exists('user_id', user['id'], 'followers'):
                    user['screen_name'] = user['screen_name'].encode('utf-8', 'replace')
                    insertFollower(user['id'], user['screen_name'], user['followers_count'])
                    print '\nAdded follower to database:', user['screen_name']
            nextCursor = results['next_cursor']
        return None
    except Exception as e:
        logging.error('BOT ERROR updateFollowers: ' + str(e))

def doTweet():    
    # Randomly execute an action according to the provided probabilities.
    c = np.random.choice(tweetProbs.keys(), 1, p=tweetProbs.values())[0]
    
    try:
        if   c == 'skip'   : stdout.write('.'), sys.stdout.flush()
        elif c == 'news'   : return tweetNews()
        elif c == 'picture': return tweetPicture()
        elif c == 'retweet': return retweet()
    except Exception as e:
        logging.error('BOT ERROR doTweet (c=' + str(c) + '): ' + str(e))
    
def doFollow():    
    # Randomly execute an action according to the provided probabilities.
    c = np.random.choice(followProbs.keys(), 1, p=followProbs.values())[0]
    
    try:
        if   c == 'skip'    : pass
        elif c == 'keyword' : return followKeyword()
        elif c == 'back'    : return followBack()
        elif c == 'related' : return followRelated()
        elif c == 'unfollow': return unfollow()
    except Exception as e:
        logging.error('BOT ERROR doFollow (c=' + str(c) + '): ' + str(e))


#######################################
### TWEETING + FOLLOWING (COMBINED) ###
#######################################

def main(sc):
    global keywords, relatedAccounts
    currTime = datetime.datetime.now().time()
    
    try:
        # Update keywords and related accounts once every hour.
        if currTime.hour == 0 and currTime.minute == 0 and currTime.second < 2:
            if trending: related.updateTrending()
            keywords = related.fetchRelated('keywords')
            relatedAccounts = related.fetchRelated('accounts')

        # Update followers once every ten minutes.
        if currTime.second == 10 and currTime.minute % 10 == 0: updateFollowers()

        # Only show activity between 8:00 AM and 10:00 PM.
        if currTime.hour >= 8 and currTime.hour <= 22:
            doTweet()
            doFollow()
    except Exception as e:
        logging.error('BOT ERROR main: ' + str(e))
        
    sc.enter(1, 1, main, (sc,))

if __name__ == '__main__':
    if trending: related.updateTrending()
    stdout.write('Now running...'), sys.stdout.flush() 
    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, main, (s,))
    s.run()
