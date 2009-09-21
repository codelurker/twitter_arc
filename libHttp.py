# -*- encoding: utf-8 -*-

"""
HTTP Processing Library
Author:  Matt Harris (matt [at] themattharris dot com)
Version: 0.2
Updated: 20 Sep 2009
License: MIT License (included file MIT-LICENSE)
"""

import urllib
import urllib2
import urlparse
import gzip

from StringIO import StringIO
import logging

# Who are we
USER_AGENT = 'libHttp/0.2 using Python urllib2'

__logger = logging.getLogger('libHttp')

class RedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        """
        Subclassed handler which prevents exceptions on PUT and POST request
        redirects and instead creates an HTTP Error with 301 as the status.
        
        This function abides by RFC2616.
        """
        __logger = logging.getLogger('libHttp.RedirectHandler')
        __logger.warning('Received HTTP Status Code 301')
        if req.get_method() not in ('PUT', 'POST'):
            result = urllib2.HTTPRedirectHandler.http_error_301(
                self, req, fp, code, msg, headers)
        else:
            result = urllib2.HTTPError(
                req.get_full_url(), code, msg, headers, fp)
        
        result.headers['X-Was-Redirected']  = str(code)
        result.headers['X-Redirected-From'] = req.get_full_url()
        return result
        
    def http_error_302(self, req, fp, code, msg, headers):
        """
        Subclassed handler which prevents exceptions on PUT and POST request
        redirects and instead creates an HTTP Error with 302 as the status.

        This function abides by RFC2616.
        """
        __logger = logging.getLogger('libHttp.RedirectHandler')
        __logger.warning('Received HTTP Status Code 302')
        if req.get_method() not in ('PUT', 'POST'):
            result = urllib2.HTTPRedirectHandler.http_error_302(
                self, req, fp, code, msg, headers)
        else:
            result = urllib2.HTTPError(
                req.get_full_url(), code, msg, headers, fp)

        result.headers['X-Was-Redirected']  = str(code) + '\r'
        result.headers['X-Redirected-From'] = req.get_full_url() + '\r'
        return result

        
class ErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        """
        Subclassed error handler for urllib2.
        """
        result = urllib2.HTTPError(
            req.get_full_url(), code, msg, headers, fp)

        return result
        

class MethodRequest(urllib2.Request):
    def __init__(self, method, *args, **kwargs):
        """
        Subclassed urllib2 request method to support other verbs like PUT and 
        DELETE
        """
        self._method = method
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method

def makeQueryString(args):
    """
    Converts given list or dictionary of args to an encoded querystring
    """
    import urllib
    return urllib.urlencode(args, True);

def fixSlashes(url):
    """
    Removes double slashes in URLs, and ensures the protocol is doubleslahed
    """
    import re
    # insert missing protocol slashes
    p = re.compile( '(:/)([^/])' )
    url = p.subn( r'\1/\2', url)[0]
    
    # strip any double slashes excluding ://
    p = re.compile( '([^:])//' )
    return p.subn( r'\1/', url)[0]

def request(source, etag=None, lastmodified=None, headers={}, debug=False,
            username='', password='', post_data=None, action='GET'):
    """
    URL, filename, or string --> stream 
    
    This function lets you define parsers that take any input source 
    (URL, pathname to local or network file, or actual data as a string) 
    and deal with it in a uniform manner.  Returned object is guaranteed 
    to have all the basic stdio read methods (read, readline, readlines). 
    Just .close() the object when you're done with it. 
    
    If the etag argument is supplied, it will be used as the value of an 
    If-None-Match request header. 
    
    If the lastmodified argument is supplied, it must be a formatted 
    date/time string in GMT (as returned in the Last-Modified header of 
    a previous request).  The formatted date/time will be used 
    as the value of an If-Modified-Since request header. 
    
    If the agent argument is supplied, it will be used as the value of a 
    User-Agent request header. 
    
    If basicauth is True, and username and password are given, the function 
    will use Basic Authentication to access the source.
    
    Data is the POST/PUT data to be sent to the server. Note this will force a 
    POST request unless the method is set to PUT.
    
    Action is the HTTP action which should take place. Note if Data is not 
    None and the action is GET, the action will be ignored and a POST will 
    take place.
    """
    __logger.debug('libHttp.request with: URL: %s\n Headers: %s\n Username: %s\n Password: %s\n Action: %s\n' % \
        (source, headers, username, password, action))
    if hasattr(source, 'read'):
        return source
    
    if source == '-':
        return sys.stdin
        
    _url = urlparse.urlparse(source)[0]
    if _url in ('http', 'https'):
        if action == 'GET':
            if post_data is not None:
                post_data = urllib.urlencode(post_data).strip()
                if post_data:
                    source = '?'.join( [source, post_data] )
            __logger.debug('URL now %s' % source)
            request = MethodRequest(action, source)
        else:
            __logger.debug('Setting post_data')
            request = MethodRequest(action, source, post_data['<payload>'])
        
        request.add_header('User-Agent', USER_AGENT)        
        request.add_header('Accept-encoding', 'gzip')
        handlers = [ RedirectHandler(), ErrorHandler() ]
        
        if username and password:
            __logger.debug('Username and password set, using Basic Authentication')
            passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            # password manager doesn't like the protocol being present
            passmgr.add_password(None, source, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passmgr)
            handlers.append(authhandler)
        if debug:
            __logger.debug('Adding Debug Handler')
            debughandler = urllib2.HTTPHandler(debuglevel=1)
            handlers.append(debughandler)
        
        opener = urllib2.build_opener(*handlers)

        if etag:
            __logger.debug('Adding eTag %s' % etag)
            request.add_header('If-None-Match', etag)                           
        if lastmodified:
            __logger.debug('Adding last modified %s' % lastmodified)
            request.add_header('If-Modified-Since', lastmodified)
        
        # add any extra headers
        if headers:
            for k, v in headers.iteritems():
                __logger.debug('Adding additional header %s: %s' % (k, v))
                request.add_header(k, v)

        return opener.open(request)
        
    # try to open with native open function (if source is a filename) 
    try:
        return open(source)
    except (IOError, OSError):
        pass

    # treat source as string 
    return StringIO(str(source))


def fetch(source, etag=None, lastmodified=None, headers={}, debug=False,
                username='', password='', post_data=None, action='GET'):
    """
    Fetch data and metadata from a URL, file, stream, or string
    """
    result = {}
    f = request(source, etag, lastmodified, headers, debug, username, 
                password, post_data, action)
    
    result['data'] = f.read()                          
    
    if hasattr(f, 'url'):
        result['url'] = f.url

    if hasattr(f, 'headers'):
        result['etag'] = f.headers.get('ETag')
        result['last_modified'] = f.headers.get('Last-Modified')
        result['headers'] = f.headers.headers
        # decompress gzipped content
        if f.headers.get('content-encoding', '') == 'gzip':
            result['data'] = gzip.GzipFile( 
                fileobj = StringIO(result['data'])).read()

    result['code'] = f.code
    result['msg']  = f.msg
    
    f.close()                                                        
    return result
    
def getResponseMessage(code, long_message=False):
    """
    Converts an HTTP status code into a meaningful message
    """
    import BaseHTTPServer
    try:
        return BaseHTTPServer.BaseHTTPRequestHandler.responses.get(code)[long_message]
    except:
        return 'No such code'