import db
def unfollow():
    " Unfollows the oldest following user that doesn't follow the bot back. "
    print db.executeQuery('SELECT * FROM follows WHERE active = 1 LIMIT 1', output=True)

unfollow()
