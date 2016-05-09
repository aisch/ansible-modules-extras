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
module: influxdb_user
short_description: Manage InfluxDB users
description:
    - Manage InfluxDB users
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
    name:
        description:
            - Name of the user to create or drop.
        required: true
    password:
        description:
            - Password of the user to create.
        required: true
    admin:
        description:
            - Whether the user is an admin.
        required: false
        default: false
    state:
        description:
            - Determines if the user should be created or dropped.
        choices: ['present', 'absent']
        default: present
        required: false
'''
EXAMPLES = '''
# Example influxdb_user command from Ansible Playbooks
- name: Create user with a password.
    influxdb_user:
      hostname: "{{influxdb_ip_address}}"
      name: "{{influxdb_user_name}}"
      password: "{{influxdb_user_password}}"
      state: present

- name: Drop user
    influxdb_user:
      hostname: "{{influxdb_ip_address}}"
      name: "{{influxdb_user_name}}"
      state: absent

- name: Create user using custom login credentials
    influxdb_user:
      hostname: "{{influxdb_ip_address}}"
      login_username: "{{influxdb_username}}"
      login_password: "{{influxdb_password}}"
      name: "{{influxdb_user_name}}"
      state: present
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
        name=dict(required=True, type='str'),
        password=dict(required=True, type='str', no_log=True),
        admin=dict(default=False, type='bool'),
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


def find_user(module, client, name):
    try:
        users = client.get_list_users()
        for user in users:
            if user['user'] == name:
                return user
    except requests.exceptions.ConnectionError as e:
        module.fail_json(msg=str(e))


def create_user(module, client, name, password, admin=False):
    if not module.check_mode:
        try:
            client.create_user(name, password, admin=admin)
        except requests.exceptions.ConnectionError as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=True)


def drop_user(module, client, name):
    if not module.check_mode:
        try:
            client.drop_user(name)
        except exceptions.InfluxDBClientError as e:
            module.fail_json(msg=e.content)

    module.exit_json(changed=True)


def grant_admin_privileges(module, client, name):
    if not module.check_mode:
        try:
            client.grant_admin_privileges(name)
        except exceptions.InfluxDBClientError as e:
            module.fail_json(msg=e.content)

    module.exit_json(changed=True)


def revoke_admin_privileges(module, client, name):
    if not module.check_mode:
        try:
            client.revoke_admin_privileges(name)
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
    user_name = module.params['name']
    password = module.params['password']
    admin = module.params['admin']

    client = connect_to_influxdb(module)
    user = find_user(module, client, user_name)

    if state == 'present':
        if user:
            if user['admin'] == admin:
                module.exit_json(changed=False)
            elif admin:
                grant_admin_privileges(module, client, user_name)
            else:
                revoke_admin_privileges(module, client, user_name)
        else:
            create_user(module, client, user_name, password)

    if state == 'absent':
        if user:
            drop_user(module, client, user_name)
        else:
            module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
