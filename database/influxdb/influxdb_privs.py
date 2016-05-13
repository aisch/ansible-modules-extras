#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: influxdb_privs
short_description: Manage InfluxDB user privileges.
description:
    - Manage InfluxDB user privileges.
version_added: 2.2
requirements:
    - "python >= 2.6"
    - "influxdb >= 0.9"
options:
    hostname:
        description:
            - The hostname or IP address on which InfluxDB server is listening.
        default: localhost
        required: false
    port:
        description:
            - The port on which InfluxDB server is listening.
        default: 8086
        required: false
    login_username:
        description:
            - Username that will be used to authenticate against InfluxDB server.
        default: root
        required: false
    login_password:
        description:
            - Password that will be used to authenticate against InfluxDB server.
        default: root
        required: false
    username:
        description:
            - Name of the user to grant or revoke privileges.
        required: true
    database:
        description:
            - Name of the database on which to grant or revoke privileges.
        required: true
    privilege:
        description:
            - The privilege to grant or revoke.
        choices: ['read', 'write', 'all']
        required: true
    state:
        description:
            - Determines if the privilege should be granted ('present') or revoked ('absent').
        choices: ['present', 'absent']
        default: present
        required: false
'''
EXAMPLES = '''
# Example influxdb_privs command from Ansible Playbooks
- name: Grant all privilege to user "todd" on database "NOAA_water_database".
    influxdb_privs:
      hostname: "{{influxdb_hostname}}"
      login_username: "{{influxdb_login_username}}"
      login_password: "{{influxdb_login_password}}"
      username: todd
      database: NOAA_water_database
      privilege: all
      state: present

- name: Revoke all privilege from user "todd" on database "NOAA_water_database".
    influxdb_privs:
      hostname: "{{influxdb_hostname}}"
      login_username: "{{influxdb_login_username}}"
      login_password: "{{influxdb_login_password}}"
      username: todd
      database: NOAA_water_database
      privilege: write
      state: absent

'''

RETURN = '''
#only defaults
'''

try:
    import requests.exceptions
    from influxdb import InfluxDBClient
    from influxdb import exceptions
    HAS_INFLUXDB = True
except ImportError:
    HAS_INFLUXDB = False


def influxdb_argument_spec():
    return dict(
        hostname=dict(default='localhost', type='str'),
        port=dict(default=8086, type='int'),
        login_username=dict(default='root', type='str'),
        login_password=dict(default='root', type='str', no_log=True),
        username=dict(required=True, type='str'),
        database=dict(required=True, type='str'),
        privilege=dict(required=True, type='str', choices=['read', 'write', 'all']),
        state=dict(default='present', type='str', choices=['present', 'absent']),
    )


def connect_to_influxdb(module):
    hostname = module.params['hostname']
    port = module.params['port']
    login_username = module.params['login_username']
    login_password = module.params['login_password']

    client = InfluxDBClient(
        host=hostname,
        port=port,
        username=login_username,
        password=login_password,
    )
    return client


def find_user(module, client, username):
    try:
        users = client.get_list_users()
        for user in users:
            if user['user'] == username:
                return user
    except requests.exceptions.ConnectionError as e:
        module.fail_json(msg=str(e))


def find_grant(module, client, privilege, database, username):
    privilege_map = {
        'READ': 'read',
        'WRITE': 'write',
        'ALL PRIVILEGES': 'all',
        'NO PRIVILEGES': None,
    }
    user = find_user(module, client, username)
    if not user:
        module.fail_json(msg='No user "{0}".'.format(username))
    try:
        grants = client.get_list_grants(username)
        for grant in grants:
            if grant['database'] != database or \
                grant['privilege'] not in privilege_map:
                continue
            if privilege_map[grant['privilege']] == privilege:
                return grant
    except requests.exceptions.ConnectionError as e:
        module.fail_json(msg=str(e))


def grant_privilege(module, client, privilege, database, username):
    if not module.check_mode:
        try:
            client.grant_privilege(privilege, database, username)
        except requests.exceptions.ConnectionError as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=True)


def revoke_privilege(module, client, privilege, database, username):
    if not module.check_mode:
        try:
            client.revoke_privilege(privilege, database, username)
        except exceptions.InfluxDBClientError as e:
            module.fail_json(msg=e.content)

    module.exit_json(changed=True)


def main():
    argument_spec = influxdb_argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    if not HAS_INFLUXDB:
        module.fail_json(msg='influxdb python package is required for this module')

    state = module.params['state']
    username = module.params['username']
    database = module.params['database']
    privilege = module.params['privilege']

    client = connect_to_influxdb(module)
    grant = find_grant(module, client, privilege, database, username)

    if state == 'present':
        if grant:
            module.exit_json(changed=False)
        else:
            grant_privilege(module, client, privilege, database, username)

    if state == 'absent':
        if grant:
            revoke_privilege(module, client, privilege, database, username)
        else:
            module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
