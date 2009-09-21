#!/usr/bin/python2.5
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
from pprint import pprint

LOGGER = 'twitter_arc'
TWEETS_FILE = '%s\'s tweets.tsv' % USERNAME
DMS_FILE = '%s\'s dms.tsv' % USERNAME
TWITTER_URL = 'http://twitter.com'
TWITTER_FORMAT = '.json'
TWITTER_COUNT = 200
LOG_FILES = 5
__logger = logging.getLogger()

def configure_logging():
    __logger.setLevel( logging.__getattribute__(LOGLEVEL))

    # rotating logger
    handler = logging.handlers.RotatingFileHandler(
                  'twitter_arc.txt', maxBytes=10240, backupCount=LOG_FILES)
    __logger.addHandler(handler)

def check_credentials():
    """Checks the username and password provided in the configuration is
    valid.
    """
    __logger.info('Checking Your Credentials with Twitter')
    response = queryAPI('/account/verify_credentials')
    return response['code'] == 200

def download_tweets(dms=False):
    page = 0
    tweets = []
    retry = False
    
    if dms:
        action='/direct_messages'
    else:
        action='/statuses/user_timeline'
    
    while True:
        args = {'count': 200, 'page':page}
        if SINCE_ID and SINCE_ID > 0:
            args['since_id'] = SINCE_ID
        if MAX_ID and MAX_ID > 0:
            args['max_id'] = MAX_ID

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
            raise ValueError, data
        else:
            retry = False

        store_tweets(data, dms)
        time.sleep(5)
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
        s = Template("${id}\t${sender_id}\t${recipient_id}\t${created_at}\t" \
            "${sender_screen_name}\t${recipient_screen_name}\t${text}\n")
    else:
        s = Template("${id}\t${created_at}\t${text}\t${source}\t" \
            "${in_reply_to_user_id}\t${in_reply_to_status_id}\t" \
            "${in_reply_to_screen_name}\t${favorited}\t${truncated}\n")
        
    return s.substitute(tweet)

def store_tweets(tweets, dms=False):
    if dms:
        filename = DMS_FILE
    else:
        filename = TWEETS_FILE
    with open(filename, 'a') as f:
        for tweet in tweets:
            __logger.debug('Writing tweet to file')
            f.write(buildTweet(tweet, dms))

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
        dms = download_tweets(dms=True)
        sys.exit(0)
        tweets = download_tweets(dm=True)

if __name__ == '__main__':
    archive_twitter()