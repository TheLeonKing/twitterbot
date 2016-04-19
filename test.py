import db

def unfollow():
    " Unfollows the oldest following user that doesn't follow the bot back. "
    uId = db.executeQuery('SELECT user_id FROM follows WHERE active = 1 LIMIT 1', output=True)[0][0]
    
    if not exists('user_id', uId, 'followers'):
        db.executeQuery('UPDATE follows SET active = 2 WHERE user_id = %s', (uId,))
        return unfollow()

    try:
        twython.destroy_friendship(user_id=uId)
        print '\nUnfollowed user with ID ' + str(uId)
    except Exception as e:
        logging.error('BOT ERROR unfollow: ' + str(e))
    
    db.executeQuery('UPDATE follows SET active = 0 WHERE user_id = %s', (uId,))
    
unfollow()
