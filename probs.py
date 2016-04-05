'''
Updates the probabilities.
'''

import db
import logging
import sys


def initProbs():
    tweetProbs = { 'news' : 0, 'picture' : 0, 'retweet' : 0, 'skip' : 1 }
    followProbs = { 'keyword' : 0, 'back' : 0, 'related' : 0, 'skip' : 1 }
    for tType, tProb in tweetProbs.iteritems():
        db.executeQuery('INSERT IGNORE INTO tweet_probs (tweet_type, tweet_prob) VALUES (%s, %s);', values=(tType, tProb))
    for fType, fProb in followProbs.iteritems():
        db.executeQuery('INSERT IGNORE INTO follow_probs (follow_type, follow_prob) VALUES (%s, %s);', values=(fType, fProb))

def fetchProbs(mode):
    '''
    Returns a list of dictionary like 'probType (str) : probValue (float)'
    indicating the current probability settings for `mode`.
    '''
    query = 'SELECT * FROM ' + str(mode) + '_probs'
    currProbs = db.executeQuery(query, output=True)
    
    # Query output is a list of tuples; convert to dict.
    return {prob[0] : prob[1] for prob in currProbs}

def printProbs(mode):
    ' Pretty prints the current probability values for `mode`. '
    currProbs = fetchProbs(mode)
    
    # Print the current probability values to the screen.
    print '\nThe following probability settings are currently set for ' + str(mode) + ':'
    for probType, probValue in currProbs.iteritems():
        print probType, ' = ', probValue, '=', int(probValue*3600), 'times per hour'

def updateProbs(mode):
    '''
    Updates the probability values for `mode` (can be
    either 'tweet' or 'follow') based on user input.
    '''
    currProbs = fetchProbs(mode)
    newProbs = {}
    
    # Print the current probability values to the screen.
    printProbs(mode)
    
    # Prompt the user for the new probability values.
    print '\nPlease enter the new desired probability values:'
    for probType, probValue in currProbs.iteritems():
        if probType != 'skip':
            userProb = promptProb(probType)
            newProbs[probType] = userProb
    
    # If the probability values are higher than 1, show an error and start over.
    if sum(newProbs.values()) > 1:
        print '\nThe probability values you entered are too high. Try again.'
        return updateProbs(mode)
    # If the probability values are lower than 1, set the 'skip' value so the total sums to 1.
    else:
        newProbs['skip'] = 1.0 - sum(newProbs.values())        
        
    # If the probability values are correct, update the database.
    for probType, probValue in newProbs.items():
        updateProb(mode, probType, probValue)
    
    print '\nProbabilities for ' + str(mode) + ' successfully updated.'
    
def promptProb(probType):
    '''
    Prompts the user to enter a probability value.
    Returns this value, or re-prompts if value is invalid.
    '''
    perHour = raw_input('How many times per hour should "' + str(probType) + '" be executed? ')
    
    # Return user input if input is float or int.
    try:
        int(perHour)
        return (int(perHour)/3600.0)
    # Show error and re-prompt if input is an integer.
    except ValueError as e:
        print 'Please enter an integer.'
        return promptProb(probType)
        
def updateProb(table, probType, probValue):
    ' Updates a single probability value (e.g. sets "skip" to 0.8 for "tweets"). '
    query = 'UPDATE ' + str(table) + '_probs SET ' + str(table) + '_prob = %s WHERE ' + str(table) + '_type = %s;'
    db.executeQuery(query, (probValue, probType))

if __name__ == '__main__':
    initProbs()
    # If first argument is 'tweet', only update tweet probs.
    if len(sys.argv) > 1 and sys.argv[1] == 'tweet':
        updateProbs('tweet')
        print '\nProbabilities for tweet updated!'
        printProbs('tweet')
    # If first argument is 'follow', only update follow probs.
    elif len(sys.argv) > 1 and sys.argv[1] == 'follow':
        updateProbs('follow')
        print '\nProbabilities for follow updated!'
        printProbs('follow')
    # If no arguments (or invalid arguments) are provided, update both.
    else:
        updateProbs('tweet')
        updateProbs('follow')
        print '\nProbabilities for tweet and follow updated!'
        printProbs('tweet')
        printProbs('follow')



