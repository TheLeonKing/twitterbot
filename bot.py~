''' The Twitter bot script that constantly runs. '''

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
logging.basicConfig(filename='errors.log', level=logging.DEBUG)

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

# Set up the bad words list.
badWords = set(line.strip('\n') for line in open('bad_words.txt'))\

# Initialize related keywords + accounts and tweet + follow probabilities.
keywords = related.fetchRelated('keywords')
relatedAccounts = related.fetchRelated('accounts')
tweetProbs = probs.fetchProbs('tweet')
followProbs = probs.fetchProbs('follow')


def bitly(url):
    ' Takes an URL, returns its shortened bit.ly URL. '
    shorten = bitlyConn.shorten(url)
    return shorten['url']

def keyword():
    ' Returns a random keyword. '
    return random.choice(keywords)

def related():
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
    
    tweet, url_bitly = generateTweet(text, url, hashtag)
    
    # If the tweet has a picture, upload it and post a media tweet.
    if pic:
        photo = (StringIO(urllib.urlopen(url).read()))
        response = twython.upload_media(media=photo)
        tweet = twython.update_status(status=tweet, media_ids=[response['media_id']])['text']
    # If this tweet doesn't have a picture, post a general tweet.
    else:
        twython.update_status(status=tweet)
    
    # Insert Tweet into database.
    insertTweet(tweet, url=url, bitly=url_bitly, pic=pic)
    
    return tweet

def generateTweet(text, url, hashtag):
    """ Generates a tweet's text. """
    # Shorten URL and set hashtag (if they are provided).
    url_bitly = bitly(url) if url else ''
    hashtag = '#' + re.sub('[^A-Za-z0-9]+', '',  hashtag) if hashtag else ''
    
    # Max text length is 140 - 25 (link length) - length hashtag - two whitespaces.
    textlength = 140 - 25 - len(hashtag) - 2
    
    # Split at space before `textlength` characters, return full tweet.
    text = textwrap.wrap(text, textlength)[0]
    return ' '.join([text, hashtag, url_bitly]), url_bitly


def exists(col, val, table='tweets'):
    ''' Checks whether a column-value pair exists, e.g.
        to check if a picture has already been tweeted. '''
    noOfResults = len(db.executeQuery('SELECT * FROM ' + table + ' WHERE ' + str(col) + ' = "' + str(val) + '"', output=True))
    return True if (noOfResults > 0) else False


################
### TWEETING ###
################

def tweetNews(keyword=keyword()):
    ' Tweets a news article (based on a keyword). '
    
    # Fetch news articles matching our keyword.
    results = gnp.get_google_news_query(keyword)
    
    # Tweet the first news article the bot hasn't tweeted about yet.
    for story in results['stories']:
        if not exists('url', story['link']):
            print '\nTweeted (news):', tweet(story['title'], url=story['link'], hashtag=keyword)
            return None

def tweetPicture(keyword=keyword(), page=1):
    ' Tweet a picture (based on a keyword). '
    
    # Find the first 100 results matching our keyword.
    results = flickr.photos.search(text=keyword, safe_search=1, content_type=1, page=1)
    
    # Loop through the results until we find a photo we haven't tweeted yet.
    for pic in results['photos']['photo']:
        if not exists('pic', pic['id']):
            pic['url'] = flickr.photos.getSizes(photo_id=pic['id'])['sizes']['size'][6]['source']
            print '\nTweeted (picture):', tweet(pic['title'], url=pic['url'], pic=int(pic['id']), hashtag=keyword)
            return None
    
    # If the loop ended, we've tweeted all pictures already --> recursively call the next page.
    findPicture(keyword, page=page+1)

def retweet(keyword=keyword()):
    '''
    Retweets the first tweet that matches the given keyword,
    only if it is (1) longer than 70 chars; (2) written in
    English; (3) positive; (4) not offensive (no swear words);
    and (5) if the bot hasn't already retweeted it.
    '''
    
    # Find the results matching the keyword.
    results = twython.search(q=keyword, lang='en')['statuses']
    
    # Calculate a score for each tweet, based on the persons no. of followers and the tweet's no. of retweets.
    for tweet in results:
        tweet['score'] = 0
        if (tweet['user']['followers_count'] > 0): tweet['score'] += np.log(tweet['user']['followers_count']) 
        if (tweet['retweet_count'] > 0): tweet['score'] += np.log(tweet['retweet_count'])
    
    # Sort results, with the highest score first.
    results = sorted(results, key=lambda k: k['score'], reverse=True)
    
    for tweet in results:
        # Correctly encode the tweet and screen name.
        tweet['text'] = tweet['text'].encode('utf-8', 'ignore')
        tweet['user']['screen_name'] = tweet['user']['screen_name'].encode('utf-8', 'ignore')
        
        # Retweet the first tweet that satisfies all the requirements.
        if longTweet(tweet) and englishTweet(tweet) and positiveTweet(tweet) and notOffensive(tweet) and not exists('id', tweet['id'], 'retweets'):
            twython.retweet(id=tweet['id'])
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

    # If Alchemy API request failed, try again after ten seconds. Give up after more than 5 failed attempt.
    except Exception as e:
        print '\nError during sentiment analysis for tweet %s. Error: %s.' % (tweet['id'], e)
        logging.warning('BOT:' + str(e))
        sleep(10)
        return False if (attempt > 5) else positiveTweet(tweet, attempt+1)


#################
### FOLLOWING ###
#################

def follow(uId, uHandle, followers, tweet=None, source=None):
    ' Follows a user and insert the follow interaction in the database. '
    uHandle = uHandle.encode('utf-8', 'ignore')
    twython.create_friendship(user_id=uId)
    insertFollow(uId, uHandle, followers, tweet, source)
    
    # Print feedback, based on whether the follow action was
    # based on a keyword or on a related account (source).
    if tweet: print '\nFollowed (keyword)', uHandle, '(', tweet, ')'
    elif source: print '\nFollowed (source)', uHandle, '(', source, ')'

def followKeyword(keyword=keyword()):
    ' Follows a user based on a keyword. '
    results = twython.search(q=keyword, lang='en', count=10)
    try:
        for tweet in results['statuses']:
            try:
                # Extract necessary information about tweet and user.
                uId = int(tweet['user']['id'])
                uHandle = tweet['user']['screen_name'].encode('utf-8', 'ignore')
                followers = tweet['user']['followers_count']
                tweet = tweet['text'].encode('utf-8', 'ignore')
                
                # Follow user and insert follow interaction in database.
                follow(uId, uHandle, followers, tweet=tweet)
                return None
            except Exception as e:
                logging.warning('BOT:' + str(e))
    except Exception as e:
        logging.warning('BOT:' + str(e))

def followBack():
    '''
    Follows the first person who follows the
    bot, but is not followed back by the bot.
    '''
    followRelated(myHandle)

def followRelated(handle=related()):
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
        logging.warning('BOT:' + str(e))

def updateFollowers():
    ' Updates the database of people who follow the bot. '
    nextCursor = -1
    try:
        # While the followers list contains more users (Twitter API has max of 200 users per request).
        while(nextCursor):
            results = twython.get_followers_list(screen_name=myHandle, count=200, cursor=nextCursor)
            
            # Only insert a user if (s)he is not already in the database.
            for user in results['users']:
                if not exists('user_id', user['id'], 'followers'):
                    user['screen_name'] = user['screen_name'].encode('utf-8', 'ignore')
                    insertFollower(user['id'], user['screen_name'], user['followers_count'])
                    print '\nAdded follower to database:', user['screen_name']
            nextCursor = results['next_cursor']
        return None
    except Exception as e:
        logging.warning('BOT:' + str(e))

def doTweet():    
    # Randomly execute an action according to the provided probabilities.
    c = np.random.choice(tweetProbs.keys(), 1, p=tweetProbs.values())[0]

    if   c == 'skip'   : stdout.write('.'), sys.stdout.flush()
    elif c == 'news'   : return tweetNews()
    elif c == 'picture': return tweetPicture()
    elif c == 'retweet': return retweet()
    
def doFollow():    
    # Randomly execute an action according to the provided probabilities.
    c = np.random.choice(followProbs.keys(), 1, p=followProbs.values())[0]

    if   c == 'skip'   : pass
    elif c == 'keyword': return followKeyword()
    elif c == 'back'   : return followBack()
    elif c == 'related': return followRelated()


#######################################
### TWEETING + FOLLOWING (COMBINED) ###
#######################################

def main(sc, trending=False):
    global keywords, relatedAccounts
    currTime = datetime.datetime.now().time()
    
    try:
        # Update keywords and related accounts once every hour.
        if currTime.minute == 0 and currTime.second < 4:
            if trending: updateTrending()
            keywords = fetchRelated('keywords')
            relatedAccounts = fetchRelated('accounts')

        # Update followers once per minute.
        if currTime.second == 10: updateFollowers()

        # Only show activity between 8:00 AM and 10:00 PM.
        if currTime.hour >= 8 and currTime.hour <= 22:
            doTweet()
            doFollow()
    except Exception as e:
        logging.warning('BOT:' + str(e))
        
    sc.enter(1, 1, main, (sc, trending))

if __name__ == '__main__':
    stdout.write('Now running...'), sys.stdout.flush() 
    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, main, (s,))
    s.run()
