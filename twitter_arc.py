#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""
Twitter Archiver
Author:  Matt Harris (matt [at] themattharris dot com)
Version: 0.1
Updated: 20 Sep 2009
License: MIT License (included file MIT-LICENSE)
"""
from __future__ import with_statement

import sys
import time
import logging
import logging.handlers
try:
    import simplejson as json
except ImportError:
    print 'Twitter_arc requires simplejson to be installed. Please visit ' \
        'http://pypi.python.org/pypi/simplejson for more information.'
    sys.exit(1)

# Import configuration
from local_settings import *

LOGGER = 'twitter_arc'
TWEETS_FILE = '%s\'s tweets.csv' % USERNAME
DMS_FILE = '%s\'s dms.csv' % USERNAME
TWITTER_URL = 'http://twitter.com'
TWITTER_FORMAT = '.json'
TWITTER_COUNT = 200
LOG_FILES = 5
__logger = logging.getLogger()

def getFilename(dms):
    if dms:
        return DMS_FILE
    else:
        return TWEETS_FILE

def configure_logging():
    try:
        __logger.setLevel(logging.__getattribute__(LOGLEVEL))
    except:
        __logger.setLevel(logging.CRITICAL)

    # rotating logger
    handler = logging.handlers.RotatingFileHandler(
                  'log', maxBytes=10240, backupCount=LOG_FILES)
    __logger.addHandler(handler)

def check_credentials():
    """Checks the username and password provided in the configuration is
    valid.
    """
    __logger.info('Checking Your Credentials with Twitter')
    response = queryAPI('/account/verify_credentials')
    return response['code'] == 200
    
def loadTweets(dms=False):
    tweets = []
    import csv
    try:
        # this will skip the header row by default
        reader = csv.reader(open(getFilename(dms)))
        for row in reader:
            tweets.append(row)
        if tweets:
            # delete the header row
            del tweets[0]
    except IOError:
        # file doesn't exist
        pass
    return tweets

def download_tweets(dms=False):
    page = 1
    tweets = loadTweets(dms)
    tweets.reverse()
    retry = False
    if not tweets:
        since_id = 0
    else:
        since_id = max(int(t[0]) for t in tweets)
    
    if dms:
        action='/direct_messages'
    else:
        action='/statuses/user_timeline'
    
    while True:
        args = {'count': 200, 'page':page}
        if since_id > 0:
            __logger.info('Requesting tweets since %s' % since_id)
            print 'Requesting tweets since %s' % since_id
            args['since_id'] = since_id
            
        __logger.info('Requesting page %s' % page)
        print 'Requesting page %s' % page
        response = queryAPI(action, args)
        
        page += 1
        
        try:
            data = json.loads(response['data'])
        except ValueError:
            data = []
            pass

        if len(data) == 0 and not retry:
            __logger.info('Response from Twitter was empty or not well formed. Asking for it again.')
            retry = True
            page -= 1
            continue
        elif len(data) == 0 and retry:
            __logger.info('No more data')
            break
        elif 'error' in data:
            __logger.debug('Houston we have a problem')
            print data['error']
            sys.exit(0)
        else:
            for tweet in data:
                tweet = buildTweet(tweet, dms)
                tweets.append(tweet)
            retry = False
        time.sleep(5)

    # we want the most recent tweet at the top
    tweets.sort(key = lambda t: int(t[0]), reverse=True)
    return tweets
    
def buildTweet(tweet, dms=False):
    """Constructs the tweet line for storage in a text file"""
    from string import Template
    
    s = tweet['text']
    # if we haven't already got a unicoded string, get one now
    if type(tweet['text']) == 'str':
        __logger.debug('Attempting to decode from latin-1')
        s = s.decode('latin-1')
    
    __logger.debug('Encoding tweet as ASCII with HTML Character replacement')
    tweet['text'] = s.encode('ascii', 'xmlcharrefreplace')
    
    if dms:
        return [tweet['id'], tweet['created_at'], tweet['sender_id'],
                tweet['sender_screen_name'], tweet['text']]
    else:
        return [tweet['id'], tweet['created_at'], tweet['favorited'],
                tweet['truncated'], tweet['in_reply_to_status_id'],
                tweet['in_reply_to_user_id'], 
                tweet['in_reply_to_screen_name'], tweet['source'], 
                tweet['text']]
                
def headers(dms=False):
    """Constructs the header row for the CSV file"""
    if dms:
        return ['ID', 'Created', 'Sender ID', 'Sender Name', 'Message']
    else:
        return ['ID', 'Created', 'Favorited', 'Truncated', 'Reply Status ID',
                'Reply User ID', 'Reply Screen Name', 'Source', 'Tweet']

def store_tweets(tweets, dms=False):
    import csv
    writer = csv.writer(open(getFilename(dms), 'w'))
    writer.writerow(headers(dms))
    for tweet in tweets:
        __logger.debug('Writing tweet to file')
        writer.writerow(tweet)
        
def queryAPI(relpath, args=None):
    import libHttp
    url = ''.join([ TWITTER_URL, relpath, TWITTER_FORMAT ])
    __logger.debug('Requesting data from Twitter')
    response = libHttp.fetch(url, username=USERNAME, password=PASSWORD,
        post_data=args)
    return response

def archive_twitter():
    __logger.info('Twitter Archiver by themattharris')
    configure_logging()
    if check_credentials():
        print "Requesting Statuses"
        tweets = download_tweets()
        store_tweets(tweets)
        print "Requesting Direct Messages"
        dms = download_tweets(dms=True)
        store_tweets(dms, True)

if __name__ == '__main__':
    archive_twitter()