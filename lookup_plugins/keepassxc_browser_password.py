# MIT License
#
# Copyright (c) 2024 Andre Lehmann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
lookup: keepassxc_browser_password
author: Andre Lehmann <aisberg@posteo.de>
short_description: retrieve a password from an opened KeePassXC database
description:
    - Retrieves a password from an opened KeePassXC database using the KeePassXC Browser protocol.
options:
    _terms:
        description:
           - an url identifying the password
        required: True
        aliases: [ url ]
    required: True
    name:
        description:
            - a name identifying the password
    group:
        description:
            - a group that the password entry is stored in
    login:
        description:
            - a login name that is associated with the password entry
notes:
    - When first querying a password, an association needs to be formed with an opened KeePassXC database. This means,
      a window of KeePassXC will pop up and ask for an association name. Once the association is formed and stored in a
      file called C(.keepassxc-assoc), the lookup will try to retrieved the given password.
    - Due to the nature of the KeePassXC protocol, a password is queried using an url. This might lead to multiple
      passwords being found. Therefore to uniquely identify a password the parameters C(name), C(group) and C(login)
      can be used to trim down the results.
    - "The plugin configuration can be controlled by defining variables in Ansible. Following variables affect the
      plugins behavior:"
    - "C(keepassxc_browser_password_socket_name): KeePass HTTPPass plugin connection URL (default:
        C(org.keepassxc.KeePassXC.BrowserServer))"
    - "C(keepassxc_browser_password_state_file): Name of the state file (default: C(.keepassxc-assoc))"
'''

EXAMPLES = '''
- name: create a mysql user with a password retrieved from KeePassXC db
  mysql_user:
    name: myuser
    password: "{{ lookup('keepassxc_browser_password', 'url=ansible://mysql-root login=myuser') }}"
'''

RETURN = '''
_raw:
  description:
    - a password
'''

from pathlib import Path

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.parsing.splitter import parse_kv

try:
    from keepassxc_browser import Connection, Identity, ProtocolError
    KEEPASSXC_BROWSER_MODULE_AVAILABLE = True
except ImportError:
    KEEPASSXC_BROWSER_MODULE_AVAILABLE = False

__version__ = '1.2.1'
__license__ = 'MIT'
__email__ = 'aisberg@posteo.de'

display = Display()


class KeePassXCBrowserPasswordLookup(object):

    CLIENT_ID = 'ansible-lookup'
    STATE_FILE_DEFAULT = '.keepassxc-assoc'
    SOCKET_NAME_DEFAULT = 'org.keepassxc.KeePassXC.BrowserServer'

    def __init__(self, state_file=None, socket_name=None):
        self.connection = None
        self.state_file = state_file or KeePassXCBrowserPasswordLookup.STATE_FILE_DEFAULT
        self.socket_name = socket_name or KeePassXCBrowserPasswordLookup.SOCKET_NAME_DEFAULT
        self.id = None
        self._open_connection()

    def _open_connection(self):
        state_file = Path(self.state_file)
        if state_file.exists():
            data = state_file.read_text()
            self.id = Identity.unserialize(self.CLIENT_ID, data)
        else:
            self.id = Identity(self.CLIENT_ID)

        self.connection = Connection(socket_name=self.socket_name)
        self.connection.connect()
        self.connection.change_public_keys(self.id)

        if not self.connection.test_associate(self.id):
            display.debug('keepassxc_browser_password: Associating with KeePassXC')
            assert self.connection.associate(self.id)
            data = self.id.serialize()
            state_file.write_text(data)
            del data

    def _close_connection(self):
        if self.connection:
            self.connection.disconnect()

    def __del__(self):
        self._close_connection()

    def get_password(self, url, filters=None):
        filters = filters or {}
        try:
            logins = self.connection.get_logins(self.id, url=url)
        except ProtocolError:
            raise LookupError("No password found for url '{}'".format(url))

        # use filters to trim down result list
        if filters:
            for login in logins:
                for k, v in filters.items():
                    if v != login[k]:
                        break
                else:
                    return login['password']

            raise LookupError("No password found for {}".format(str({'url': url, **filters})))

        # get password for given url
        return logins[0]['password']


class LookupModule(LookupBase):

    def _parse_parameters(self, term):
        if isinstance(term, str):
            params = parse_kv(term)
        elif isinstance(term, dict):
            params = term
        else:
            raise AnsibleParserError(
                "Unsupported parameter type '{}' passed to keepassxc_browser_password lookup.".format(type(term)))

        url = params.get('url', None)

        if '_raw_params' in params:
            if not url:
                url = ''.join((params['_raw_params']))
            del params['_raw_params']

        if not url:
            raise AnsibleParserError("Missing 'url' parameter for keepassxc_browser_password lookup")

        # check for invalid parameters
        valid_params = frozenset(('url', 'name', 'login', 'group'))
        invalid_params = frozenset(params.keys()).difference(valid_params)
        if invalid_params:
            raise AnsibleParserError("Unrecognized parameter(s) given to keepassxc_browser_password lookup: {}".format(
                ', '.join(invalid_params)))

        if 'url' in params:
            del params['url']
        filters = params

        return url, filters

    def run(self, terms, variables=None, **kwargs):
        if not KEEPASSXC_BROWSER_MODULE_AVAILABLE:
            raise AnsibleError(
                "The keepassxc_browser module is required to use the keepassxc_browser_password lookup plugin")

        # get configuration parameters for the plugin
        variables = variables or {}
        state_file = variables.get("keepassxc_browser_password_state_file",
                                   KeePassXCBrowserPasswordLookup.STATE_FILE_DEFAULT)
        socket_name = variables.get("keepassxc_browser_password_socket_name",
                                    KeePassXCBrowserPasswordLookup.SOCKET_NAME_DEFAULT)

        try:
            lookup = KeePassXCBrowserPasswordLookup(state_file, socket_name)
        except ProtocolError as excp:
            raise AnsibleError("Failed to establish a connection to KeePassXC: {}".format(excp))
        except Exception as excp:
            raise AnsibleError("KeePassXC password lookup execution failed: {}".format(excp))

        terms.append(kwargs)
        ret = []
        try:
            for term in terms:
                url, filters = self._parse_parameters(term)
                display.vvvv("keepassxc_browser_password: {}".format(str({'url': url, **filters})))
                ret.append(lookup.get_password(url=url, filters=filters))
        except Exception as ex:
            raise AnsibleError(str(ex))
        finally:
            del lookup

        return ret
