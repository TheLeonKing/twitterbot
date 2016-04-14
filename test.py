import feedparser

x = feedparser.parse('https://news.google.com/news/section?ned=us&output=rss&q=ferrari')
for bla in x:
    print bla
