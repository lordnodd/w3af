'''
unSSL.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
from core.controllers.misc.levenshtein import relative_distance_boolean

import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity


class unSSL(baseAuditPlugin):
    '''
    Find out if secure content can also be fetched using http.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)
        
        # Internal variables
        self._first_run = True
        self._ignore_next_calls = False

    def audit(self, freq ):
        '''
        Check if the protocol specified in freq is https and fetch the same URL using http. 
        ie:
            - input: https://a/
            - check: http://a/
        
        @param freq: A fuzzableRequest
        '''
        if self._ignore_next_calls:
            return
        else:            
            # Define some variables
            secure = freq.getURL()
            insecure = secure.setProtocol('http')
            
            if self._first_run:
                try:
                    self._uri_opener.GET( insecure )
                except:
                    # The request failed because the HTTP port is closed or something like that
                    # we shouldn't test any other fuzzable requests.
                    self._ignore_next_calls = True
                    msg = 'HTTP port seems to be closed. Not testing any other URLs in unSSL.'
                    om.out.debug( msg )
                    return
                else:
                    # Only perform the initial check once.
                    self._first_run = False
                
            # It seems that we can request the insecure HTTP URL
            # (checked with the GET request)
            if 'HTTPS' == freq.getURL().getProtocol().upper():

                # We are going to perform requests that (in normal cases)
                # are going to fail, so we set the ignore errors flag to True
                self._uri_opener.ignore_errors( True )
                
                https_response = self._uri_opener.send_mutant(freq)
                freq.setURL( insecure )
                http_response = self._uri_opener.send_mutant(freq)
                
                if http_response.getCode() == https_response.getCode():
                    
                    if relative_distance_boolean( http_response.getBody(),
                                                  https_response.getBody(),
                                                  0.97 ):
                        v = vuln.vuln( freq )
                        v.setPluginName(self.getName())
                        v.setName( 'Secure content over insecure channel' )
                        v.setSeverity(severity.MEDIUM)
                        msg = 'Secure content can be accesed using the insecure protocol HTTP.'
                        msg += ' The vulnerable URLs are: "' + secure + '" - "' + insecure + '" .'
                        v.setDesc( msg )
                        v.setId( [http_response.id, https_response.id] )
                        kb.kb.append( self, 'unSSL', v )
                        om.out.vulnerability( v.getDesc(), severity=v.getSeverity() )

                # Disable error ignoring
                self._uri_opener.ignore_errors( False )
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin verifies that URL's that are available using HTTPS aren't available over an insecure
        HTTP protocol.

        To detect this, the plugin simply requests "https://abc/a.asp" and "http://abc.asp" and if both are 
        equal, a vulnerability is found.
        '''
