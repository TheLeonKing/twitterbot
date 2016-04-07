'''
Updates the related keywords/accounts.
'''

import db
import ConfigParser
import logging
import nltk
import re
import requests
import sys

from collections import Counter
from nltk.corpus import stopwords
from twython import Twython


# Read the config file.
config = ConfigParser.ConfigParser()
config.read('config.ini')

# Set up the error file.
logging.basicConfig(filename='errors.log', level=logging.WARNING)

# Set up the Twitter API.
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

# Set up the bad words and stopwords list.
badWords = set(line.strip('\n') for line in open('bad_words.txt'))
nltk.download('stopwords')
stop = stopwords.words('english')


def notOffensive(keyword):
    " Checks if a (series of) keyword(s) doesn't contain bad words. "
    for word in re.findall(r"[A-Za-z]+|\S", keyword):
        if word in badWords:
            return False
    return True

def findRelatedKeywords(keyword, keywords):
    ' Takes a keyword, returns a list of related keywords. '
    words = matchingWords(keyword)
    return findKeywords(words, keywords)

def matchingWords(keyword):
    '''
    Returns a list of words from (at least) 500 tweets that
    occur in the search query of the provided keyword.
    '''
    words = []
    seen = []
    maxId = None
    while(len(seen) < 500):
        try:
            if maxId: results = twython.search(q=keyword, lang='en', max_id=maxId, count=100)
            else: results = twython.search(q=keyword, lang='en', count=100)
            
            for tweet in results['statuses']:
                if tweet['id'] not in seen:
                    seen.append(tweet['id'])
                    for word in re.findall(r"[A-Za-z]+|\S", tweet['text']):
                        words.append(word)
            maxId = int(seen[-1])-1 # -1 because max_id is inclusive.
        except Exception as e:
            logging.warning('RELATED:' + str(e))
            return []
    
    return words

def findKeywords(words, keywords):
    '''
    Returns a list of keywords (most meaningful
    words) based on a list of words.
    
    Requirements for a keyword:
    - Rel. frequency is higher than 1/800.
    - Word is longer than 3 characters.
    - Word is not a stopword.
    - Keyword is not yet present in the database (`keywords` list).
    - Keyword is not offensive.

    '''
    
    # Convert the words list to a counter.
    wordsC = Counter(words)
    totFreq = sum(wordsC.values())
    newKeywords = []

    # Only add words that satisfy the requirements (see docstring).
    for word, freq in wordsC.iteritems():
        word = word.lower()
        if freq > (totFreq/800.0) and len(word) > 3 and word not in stop \
        and word not in keywords and word not in newKeywords and notOffensive(word):
            newKeywords.append(word)
    
    # Convert keywords to lowercase.
    newKeywords = [x.lower() for x in newKeywords]
    
    return newKeywords

def findRelatedAccounts(keywords, accounts=[]):
    '''
    Takes a list of keywords and accounts, returns a list
    of accounts that are related to those keywords + not
    in the provided list of accounts.
    '''
    related = {}

    # Find 20 popular accounts for each keyword
    # and add them to the `related` dict.
    for keyword in keywords:
        results = twython.search_users(q=keyword, count=20)
        for user in results:
            # Only add accounts that are not yet in the database.
            if user['screen_name'] not in accounts:
                related[user['screen_name']] = user['followers_count']

    # Sort: accounts with most followers first. Only keep top 10.
    related = sorted(related, key=related.get, reverse=True)
    if len(related) > 10: related = related[:10]

    return related

def insertRelated(item, table):
    ' Inserts a keyword/related account into the database. '
    column = table[:-1] # Column is table name minus trailing 's' (e.g. 'keywords' --> 'keyword').
    query = 'INSERT IGNORE INTO ' + str(table) + ' (' + str(column) + ') VALUES (%s);'
    db.executeQuery(query, (item,))

def promptItem(item):
    '''
    Prompts the user whether he wants to add a keyword or
    related account (returns True/False accordingly).
    '''
    response = raw_input('Add "' + str(item) + '" (y/n)? ')
    
    # Return True/False based on answer, or re-prompt if input is invalid.
    if response.lower() == 'y': return True
    elif response.lower() == 'n': return False
    else: return promptItem(item)

def userUpdate(relatedItems, mode):
    '''
    Updates the related keywords/accounts database
    table based on the user's response.
    Mode can be either 'keywords' or 'accounts'.
    '''
    
    # Print returned related keywords/accounts.
    print 'Found ' + str(mode) + ':', ', '.join(relatedItems)
    added = []
    
    # Ask if the user wants to add this keyword/account.
    # If so, update the database.
    for item in relatedItems:
        add = promptItem(item)
        if add:
            insertRelated(item, mode)
            added.append(item)

    # Print the keywords/accounts the user decided to add.
    print 'Done. Added the following ' + str(mode) + ':', ', '.join(added)

def fetchRelated(mode):
    ''' Returns a list of all related keywords/accounts in the database. '''
    query = 'SELECT * FROM ' + str(mode)
    relatedItems = db.executeQuery(query, output=True)
    
    # Query output is a list of singleton tuples; convert this to a list.
    if relatedItems is None: return []
    return [x[0] for x in relatedItems]

def printRelated(mode):
    ''' Pretty prints the related keywords/accounts. '''
    related = fetchRelated(mode)
    if len(related) == 0: print '\nThe database currently contains no ' + str(mode) + '.\n'
    else: print '\nThe database currently contains the following ' + str(mode) + ': ' + ', '.join(related)  + '\n'

def updateKeywords():
    '''
    Finds keywords that are related to a single keyword and
    adds them to the database (if the user wishes to).
    '''
    
    # Print the related keywords and let the user choose one (or a totally new one).
    printRelated('keywords')
    userItem = raw_input('For which keyword do you want to find related keywords? ')
    
    # Find the keywords related to this keyword and ask the user
    # which of those (s)he wants to enter in the database.
    if len(userItem.strip()) > 3:
        keywords = fetchRelated('keywords')
        relatedItems = findRelatedKeywords(userItem, keywords)
        userUpdate(relatedItems, 'keywords')
    
    # If the user entered a keyword that's too short, show an error and re-prompt for a keyword.
    else:
        print 'You should input a single term.'
        updateKeywords()
        
def updateAccounts():
    '''
    Finds accounts that are related to the full
    list of keywords present in the database.
    '''
    
    # Fetch the related keywords and find the accounts related to those.
    keywords = fetchRelated('keywords')
    accounts = fetchRelated('accounts')
    relatedAccounts = findRelatedAccounts(keywords, accounts)
    
    # Ask the user which of the returned accounts (s)he wants to enter in the database.
    userUpdate(relatedAccounts, 'accounts')

def updateTrending():
    ' Update the trending keywords and their related accounts. '
    keywords = findTrendingTopics()
    relatedAccounts = findRelatedAccounts(keywords)
    updateRelatedTrending(keywords, 'keywords')
    updateRelatedTrending(relatedAccounts, 'accounts')

def updateRelatedTrending(items, table):
    '''
    Truncates the related keywords/accounts table
    before inserting new ones.
    '''
    db.executeQuery('TRUNCATE TABLE ' + str(table))
    for item in items:
        insertRelated(item, table)        
    
def findTrendingTopics(woeId=23424977, n=10):
    '''
    Returns the top `n` trending topics
    for a specified woeId.
    
    Default: top 10 of United States.
    '''
    results = twython.get_place_trends(id=woeId)[0]
    return [trend['name'] for trend in results['trends'][:n]]

if __name__ == '__main__':
    # If first argument is 'keywords', only update keywords.
    if len(sys.argv) > 1 and sys.argv[1] == 'keywords':
        updateKeywords()
        print '\nRelated keywords updated!'
        printRelated('keywords')
    # If first argument is 'accounts', only update accounts.
    elif len(sys.argv) > 1 and sys.argv[1] == 'accounts':
        updateAccounts()
        print '\nRelated accounts updated!'
        printRelated('accounts')
    # If no arguments (or invalid arguments) are provided, update both.
    else:
        updateKeywords()
        updateAccounts()
        print '\nRelated keywords and accounts updated!'
        printRelated('keywords')
        printRelated('accounts')

