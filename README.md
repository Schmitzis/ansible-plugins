<a name="readme-top"></a>

# Ansible Plugins

This repository contains custom Ansible plugins that can be used in Ansible Roles and Playbooks.

**Table of contents:**

- [Installation](#installation)
- [Lookup Plugins](#lookup-plugins)
  - [Installation](#installation-1)
  - [Reference](#reference)
    - [`default4dist`](#default4dist)
    - [`keepassxc_browser_password`](#keepassxc_browser_password)
      - [Automatic Login (SSH And Become Password Lookup)](#automatic-login-ssh-and-become-password-lookup)
      - [Automatic Vault Decryption](#automatic-vault-decryption)
    - [`keepass_http_password`](#keepass_http_password)
- [Filter Plugins](#filter-plugins)
  - [Reference](#reference-1)
    - [`pbkdf2_hash`](#pbkdf2_hash)
    - [`selectattr2`](#selectattr2)
    - [`slugify`](#slugify)
    - [`split`](#split)
    - [`to_gvariant`](#to_gvariant)
    - [`to_very_nice_yaml`](#to_very_nice_yaml)
- [Test Plugins](#test-plugins)
  - [Reference](#reference-2)
    - [`boolean`](#boolean)
    - [`list`](#list)
- [Modules](#modules)
  - [Reference](#reference-3)
    - [`random_password`](#random_password)
- [License](#license)
- [Author Information](#author-information)

---

## Installation

You have different options on where to install and where to use the plugins in your project. Essentially you just have to drop the plugin file (`*.py`) that you want to install into the correct directory, more on that in a second. Some of the plugins also require external dependencies to be installed on your system. Installing these dependencies can be daunting if you don't have a good understanding of the intricacies of Python. I recommend installing Ansible using _PIPX_ as described in the [official Ansible docs](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installing-and-upgrading-ansible-with-pipx) and than adding the dependencies. Here is a quick rundown:

1. Install PIPX:
    - Debian: `apt-get update && apt-get install pipx`
    - Arch Linux: `pacman -Sy python-pipx`
2. Install Ansible: `pipx install --include-deps ansible`
3. Install the dependencies: `pipx inject ansible some_dependency another_dependency`

Copying the plugin files:

**Role Level**

If you want to use a plugin in one of your roles put the plugins in your role directory in the correct dir:

```plaintext
your_name.your_role
├── defaults, tasks, etc.   # standard role dirs
├── library                 # Complex logic that you rather want to implement via Python; will be made available as a task module
├── filter_plugins          # Jinja filters, e.g.: {{ "abc" | upper }}
└── test_plugins            # Jinja tests, e.g.: {% if [1,2,3] is list %}
```

**Root Level**

If you want to make a plugin available throughout your Ansible project, you can add the plugins here:

```plaintext
ansible-playbooks
├── roles, host_vars, etc.  # standard project dirs
└── plugins                 # for organizing your plugins
    ├── modules             # Complex logic that you rather want to implement via Python; will be made available as a task module
    ├── filter_plugins      # Jinja filters, e.g.: {{ "abc" | upper }}
    ├── lookup_plugins      # Variable lookups, e.g.: "{{ lookup('password', '/tmp/passwordfile') }}"
    └── test_plugins        # Jinja tests, e.g.: {% if [1,2,3] is list %}
```

Then edit your `ansible.cfg` in the root of your project:

```ini
[defaults]
# add local ./plugins/ path as source for plugins
library            = ./plugins/modules:~/.ansible/plugins/modules:/usr/share/ansible/plugins/modules
action_plugins     = ./plugins/action:~/.ansible/plugins/action:/usr/share/ansible/plugins/action
cache_plugins      = ./plugins/cache:~/.ansible/plugins/cache:/usr/share/ansible/plugins/cache
callback_plugins   = ./plugins/callback:~/.ansible/plugins/callback:/usr/share/ansible/plugins/callback
connection_plugins = ./plugins/connection:~/.ansible/plugins/connection:/usr/share/ansible/plugins/connection
lookup_plugins     = ./plugins/lookup:~/.ansible/plugins/lookup:/usr/share/ansible/plugins/lookup
inventory_plugins  = ./plugins/inventory:~/.ansible/plugins/inventory:/usr/share/ansible/plugins/inventory
vars_plugins       = ./plugins/vars:~/.ansible/plugins/vars:/usr/share/ansible/plugins/vars
filter_plugins     = ./plugins/filter:~/.ansible/plugins/filter:/usr/share/ansible/plugins/filter
test_plugins       = ./plugins/test:~/.ansible/plugins/test:/usr/share/ansible/plugins/test
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## Lookup Plugins

Lookup plugins allow Ansible to access data from outside sources. Lookups are used as follows:

```yaml
- set_fact:
    # retrieve or generate a random password
    var: "{{ lookup('password', '/tmp/passwordfile') }}"
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



### Installation

To install one or more _lookups_ in an Ansible Playbook or Ansible Role, add a directory named `lookup_plugins` and place the _lookups_ (Python scripts) inside it.

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



### Reference

#### `default4dist`

Creates distribution dependent values.

The default4dist lookup looks for a variable by a name prefix in combination with the OS distribution or family name and returns its value. This means, you don't have to create long chains of `ansible_distribution == 'Foo'` statements to build distribution dependent values.

The lookup will search for variables in form of `{prefix}{suffix}` or `{prefix}_{suffix}`. The first found variable will be used or optional combined (dict or list) with a default value. The suffix is constructed in the following order of precedence: 

- `{distribution}_{release}_{version}`
- `{distribution}_{release}_{major_version}`
- `{distribution}_{release}`
- `{distribution}_{version}`
- `{distribution}_{major_version}`
- `{distribution}`
- `{familiy}_{release}_{version}`
- `{familiy}_{release}_{major_version}`
- `{familiy}_{release}`
- `{familiy}_{version}`
- `{familiy}_{major_version}`
- `{familiy}`
- `default`

OS distribution and family names must be specified in lower case.

**Example:**

```yaml
# a simple value that differs on different Linux distributions
myvar: "{{
    'foo' if ansible_distribution == 'Debian' else
    'bar' if ansible_distribution == 'CentOS' and ansible_distribution_release == 'Stream' else
    'bar' if ansible_distribution == 'CentOS' and ansible_distribution_major_version == '8' else
    'baz'
}}"
# can be replaced by:
_myvar_default: baz
_myvar_debian: foo
_myvar_centos_stream: bar
_myvar_centos_8: foobar
myvar: "{{ lookup('default4dist', '_myvar') }}"


# a dictionary that contains some distribution dependent values
myvar: "{{
    {'a': 1, 'b': foo} if ansible_distribution == 'Debian' else
    {'a': 2, 'b': bar} if ansible_distribution == 'CentOS' and ansible_distribution_release == 'Stream' else
    {'a': 3, 'b': bar} if ansible_distribution == 'CentOS' and ansible_distribution_major_version == '8' else
    {'a': 1, 'b': baz}
}}"
# can be replaced by:
_myvar_default: {'a': 1, 'b': baz}
_myvar_debian: {'b': foo}
_myvar_centos_stream: {'a': 2, 'b': bar}
_myvar_centos_8: {'a': 3, 'b': bar}
myvar: "{{ lookup('default4dist', '_myvar', recursive=True) }}"
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `keepassxc_browser_password`

Retrieves a password from an opened KeePassXC database using the KeePassXC Browser protocol.

The plugin allows to automatically load sensitive information from KeePassXC into Ansible, thus can be used as an addition to or even replacement of the Ansible vault. Besides loading passwords for your database for example, you can also load the Ansible _become_ or _SSH_ password and avoid retyping it over and over again.

The KeePass Lookup allows to retrieve password from an opened KeePass database and use them directly in Ansible. The plugin works like any of the KeePass browser plugins, it connects to a local port via HTTP, forms an (cryptographic) association and is then able to retrieve passwords.

The entries in the database need to be properly named. First of all the entries must have a valid URL, because the protocol returns entries by matching a given URL. The URL must consists at least of a scheme and a hostname (e.g. 'https://foo', don't use a random scheme, KeePass doesn't like that). Searching only by an URL might not return a unique result, therefore the results can be trimmed down by adding filters for the entry `name` or `login`. See the plugin documentation for more information.


**Installation:**

The plugin requires the Python [`keepassxc_browser`](https://github.com/hrehfeld/python-keepassxc-browser) module. If you installed Ansible using PIPX as described in the [Installation](#installation) section, then just run the following command to get the dependency:

```sh
pipx inject ansible keepassxc-browser
```

**Example:**

```yml
- set_fact:
    # simple password lookup by URL
    var1: "{{ lookup('keepassxc_browser_password', 'https://example.org') }}"
    # password lookup by URL and login name
    # the protocol part 'ansible://' is required to form a valid URL, it doesn't have to be 'https://' or else
    var2: "{{ lookup('keepassxc_browser_password', 'url=ansible://mysql login=root') }}"
    # password lookup by URL and name
    var3: "{{ lookup('keepassxc_browser_password', 'url=ansible://secret name=\"My Secret\"') }}"
    # password lookup by URL and group
    var4: "{{ lookup('keepassxc_browser_password', 'url=ansible://secret group=department_x') }}"
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



##### Automatic Login (SSH And Become Password Lookup)

You can use the plugin to lookup the _Become_  and/or _SSH_ passwords on Ansible startup, so you don't have to type these in all the time. There are two things you need to do to make it work:

1. Add a lookup for your _Become_  and/or _SSH_ passwords:
    ```yml
    # group_vars/all
    _ansible_become_pass: "{{ lookup('keepass_http_password', 'ansible://linux-user login=foo') }}"
    _ansible_ssh_pass: "{{ lookup('keepass_http_password', 'ansible://linux-user login=foo') }}"
    ```

2. Statically evaluate the `ansible_ssh_pass` and `ansible_become_pass` in your playbook. This is a necessary step to avoid a relatively "slow" password lookup for every single task, because Ansible won't cache any lookups:
    ```yaml
    # playbook.yml
    - hosts: xxx
      pre_tasks:
        - set_fact:
            ansible_ssh_pass: "{{ ansible_ssh_pass | default(_ansible_ssh_pass) | default(omit) }}"
            ansible_become_pass: "{{ ansible_become_pass | default(_ansible_become_pass) | default(omit) }}"
          tags: always
          no_log: true
    ```

##### Automatic Vault Decryption

It is also possible to automate the vault decryption, it requires an additional script to accomplish though. I created a [Vault Password Client Script](https://docs.ansible.com/ansible/latest/user_guide/vault.html#vault-password-client-scripts) for that purpose, that reuses some of the code of the lookup plugin:

`vault-pass-client.py` :
```python
import argparse
import sys
from pathlib import Path

from ansible.errors import AnsibleError

RELATIVE_PATH_TO_PLUGIN_DIR = '../../plugins/lookup/'

sys.path.append(str(Path(__file__).parent.joinpath(RELATIVE_PATH_TO_PLUGIN_DIR).resolve()))
from keepassxc_browser import Connection, Identity, ProtocolError
from keepassxc_browser_password import KeePassXCBrowserPasswordLookup

__author__  = 'Andre Lehmann'
__email__   = 'aisberg@posteo.de'
__version__ = '1.1.0'
__license__ = 'MIT'


def main():
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--vault-id', dest='vault_id', required=True, help='The vault ID')
    args = parser.parse_args(sys.argv[1:])

    try:
        lookup = KeePassXCBrowserPasswordLookup()
    except ProtocolError as excp:
        raise AnsibleError("Failed to establish a connection to KeePassXC: {}".format(excp))
    except Exception as excp:
        raise AnsibleError("KeePassXC password lookup execution failed: {}".format(excp))

    try:
        url = 'ansible://ansible-vault'
        filters = dict(login=args.vault_id)
        vault_pass = lookup.get_password(url=url, filters=filters)
    except Exception as ex:
        del lookup
        raise AnsibleError(str(ex))

    sys.stdout.write(vault_pass + '\n')


if __name__ == '__main__':
    main()
```

The script needs to be saved as `*-client.py` in order to work. One thing that need to be changed, is the path (`RELATIVE_PATH_TO_PLUGIN_DIR`) to the plugin dir containing the keepassxc_browser_password lookup plugin. That's done, you can use it as follows:

1. Save the vault password in KeePassXC:
   - Username: `myuser`
   - Password: `myvaultpass`
   - URL: `ansible://ansible-vault`
2. Run Ansible: `ansible-playbook --vault-id myuser@/path/to/vault-pass-client.py ...`

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `keepass_http_password`

Retrieves a password from an opened KeePass database using the KeePass HTTP protocol.

The KeePass Lookup allows to retrieve password from an opened KeePass database and use them directly in Ansible. The plugin works like any of the KeePass browser plugins, it connects to a local port via HTTP, forms an (cryptographic) association and is then able to retrieve passwords.

The entries in the database need to be properly named. First of all the entries must have a valid URL, because the protocol returns entries by matching a given URL. The URL must consists at least of a scheme and a hostname (e.g. 'https://foo', don't use a random scheme, KeePass doesn't like that). Searching only by an URL might not return a unique result, therefore the results can be trimmed down by adding filters for the entry `name` or `login`. See the plugin documentation for more information.


This plugin works much like the [`keepassxc_browser_password`](#keepassxc_browser_password) plugin and offers similar features.

**Installation:**

To use the plugin you have to perform the following steps:

1. Install KeePassHttp plugin: https://github.com/pfn/keepasshttp/
2. Install [`keepasshttp`](https://github.com/cyrbil/python_keepass_http) Python module: `pipx inject ansible keepasshttp`
3. Open KeePass and configure the KeePassHttp plugin to match the schemes: _Tools_ ➞ _KeePassHttp Options..._ ➞ _General_ ➞ _Match URL schemes_

**Example:**

```yml
- set_fact:
    # simple password lookup by URL
    var1: "{{ lookup('keepass_http_password', 'https://example.org') }}"
    # password lookup by URL and login name
    # the protocol part 'ansible://' is required to form a valid URL, it doesn't have to be 'https://' or else
    var2: "{{ lookup('keepass_http_password', 'url=https://mysql login=root') }}"
    # password lookup by URL and name
    var3: "{{ lookup('keepass_http_password', 'url=https://secret name=\"My Secret\"') }}"
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## Filter Plugins

Filters are used to transform data inside template expressions. In general filters are used in the following fashion:

```jinja
# apply a filter to `some_variable`
{{ some_variable | filter }}

# apply a filter with extra arguments
{{ some_variable | filter(arg1='foo', arg2='bar') }}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



### Reference

#### `pbkdf2_hash`

Create a password hash using pbkdf2.

**Example:**

```jinja
{{ plain_password | pbkdf2_hash(rounds=50000, scheme='sha512') }}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `selectattr2`

Filter a sequence of objects by applying a test to the specified attribute of each object, and only selecting the objects with the test succeeding.

The built-in Jinja2 filter [`selectattr`](https://jinja.palletsprojects.com/en/2.11.x/templates/#selectattr) fails whenever the attribute is missing in one or more objects of the sequence. The `selectattr2` is designed to not fail under such conditions and allows to specify a default value for missing attributes.

Examples:
```jinja
# select objects, where the attribute is defined
{{ users | selectattr2('name', 'defined') | list }}

# select objects, where the attribute is equal to a value
{{ users | selectattr2('state', '==', 'present', default='present') | list }}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `slugify`

Convert a string to a slug representation.

The filter converts strings into slugs by removing non alphanumerics, underscores, or hyphens, converting to lower case and stripping leading and trailing whitespace, dashes, and underscores.

Examples:
```jinja
{{ 'Hello World' | slugify() }} -> 'hello-world'
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `split`

Split a string by a specified seperator string.

Splitting a string with Jinja can already accomplished by executing the `split` method on strings (e.g. `"Hello World".split(" ")`), but when you want to use split in combination with "map" for example, you need a filter like this one.

Examples:
```jinja
# split a simple string
{{ 'Hello World' | split(' ') }} -> ['Hello', 'World']

# split strings in combination with 'map'
{{ ['1;2;3', 'a;b;c'] | map('split', ';') | list }} -> [['1', '2', '3'], ['a', 'b', 'c']]
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `to_gvariant`

Convert a value to GVariant Text Format.

**Example:**

```jinja
{{ [1, 3.14, True, "foo", {"bar": 0}, ("foo", "bar")] | to_gvariant() }}
-> [1, 3.14, true, 'foo', {'bar': 0}, ('foo', 'bar')]
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `to_very_nice_yaml`

Similar to Ansibles built-in `to_nice_yaml`, but it dumps multi line strings as `|` blocks without line wrapping.

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## Test Plugins

Tests are used to evaluate template expressions and return either True or False. Tests are used as follows:

```jinja
# using a test on `some_variable`
{% if some_variable is test %}{% endif %}

# a test with extra arguments
{% if some_variable is test(arg1='foo', arg2='bar') %}{% endif %}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



### Reference

#### `boolean`

Test if a value is of type boolean.

This test plugin can be used until Ansible adapts Jinja2 version 2.11, which comes with this filter built-in ([see](https://jinja.palletsprojects.com/en/2.11.x/templates/#boolean)). 

**Example:**

```jinja
{% if foo is boolean %}{{ foo | ternary('yes', 'no') }}{% endif %}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



#### `list`

Test if a value a list or generator type.

Jinja2 provides the tests `iterable` and `sequence`, but those also match strings and dicts as well. To determine, if a value is essentially a list, you need to check the following:

    value is not string and value is not mapping and value is iterable

This test is a shortcut, which allows to check for a list or generator simply with:

    value is list

**Example:**

```jinja
{% if foo is list %}{{ foo | join(', ') }}{% endif %}
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## Modules

Lookup plugins allow Ansible to access data from outside sources. Lookups are used as follows:

```yaml
- set_fact:
    # retrieve or generate a random password
    var: "{{ lookup('password', '/tmp/passwordfile') }}"
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



### Reference

#### `random_password`

Generate a random password and optionally save it to a file on the target. Differently than the built-in `password` lookup, this module creates and saves the passwords on the target host. This can be useful for creating idempotent secrets you don't want to manage locally.

**Example:**

```yaml
# Generate a random password with default settings and save it to /etc/ansible/password
- name: Generate and save a password
  random_password:

# Generate a random password using a custom character set and assign it to the 'my_password' variable
- name: Generate and assign a password
  random_password:
    chars: "digits, punctuation"
    length: 12
    var_name: my_password

# Generate a random password and set specific file permissions and ownership
- name: Generate and set file permissions
  random_password:
    mode: 0600
    owner: ansible
    group: ansible
```

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## License

MIT

<p align="right"><a href="#readme-top"><b>back to top ⇧</b></a></p>



## Author Information

Andre Lehmann (aisberg@posteo.de)
