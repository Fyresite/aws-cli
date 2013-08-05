# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
This customization adds the following scalar parameters to the
authorize operations:

* --protocol: tcp | udp | icmp or any protocol number
* --port:  A single integer or a range (min-max). You can specify ``all``
  to mean all ports (for example, port range 0-65535)
* --source-group-name
* --source-group-id
* --cidr -  The CIDR range. Cannot be used when specifying a source or
  destination security group.
"""
import logging

from awscli.customizations import CustomArgument


logger = logging.getLogger(__name__)

EVENTS = [
        'building-argument-table.ec2.AuthorizeSecurityGroupIngress',
        'building-argument-table.ec2.AuthorizeSecurityGroupEgress',
        'building-argument-table.ec2.RevokeSecurityGroupIngress',
        'building-argument-table.ec2.RevokeSecurityGroupEgress'
        ]
PROTOCOL_DOCS = ('<p>The IP protocol of this permission.</p>'
                 '<p>Valid protocol values: <code>tcp</code>, '
                 '<code>udp</code>, <code>icmp</code></p>')
PORT_DOCS = ('<p>For TCP or UDP: The range of ports to allow.'
             '  A single integer or a range (min-max). You can '
             'specify <code>all</code> to mean all ports</p>')
CIDR_DOCS = '<p>The CIDR IP range.</p>'
SOURCEGROUP_DOCS = ('<p>The name of the source security group. '
                    'Cannot be used when specifying a CIDR IP address.')
GROUPOWNER_DOCS = ('<p>The AWS account ID that owns the source security '
                   'group. Cannot be used when specifying a CIDR IP '
                   'address.</p>')

def register_secgroup(event_handler):
    for event in EVENTS:
        event_handler.register(event, _add_params)


def _build_ip_permissions(params, key, value):
    logger.debug('_build_ip_permissions: %s=%s', key, value)
    if 'ip_permissions' not in params:
        params['ip_permissions'] = [{}]
    if key == 'CidrIp':
        if 'IpRanges' not in params['ip_permissions'][0]:
            params['ip_permissions'][0]['IpRanges'] = []
        params['ip_permissions'][0]['IpRanges'].append(value)
    elif key in ('GroupId', 'GroupName', 'UserId'):
        if 'UserIdGroupPairs' not in params['ip_permissions'][0]:
            params['ip_permissions'][0]['UserIdGroupPairs'] = [{}]
        params['ip_permissions'][0]['UserIdGroupPairs'][0][key] = value
    else:
        params['ip_permissions'][0][key] = value


def _add_params(argument_table, operation, **kwargs):
    arg = ProtocolArgument(operation, 'protocol',
                           documentation=PROTOCOL_DOCS)
    argument_table['protocol'] = arg
    arg = PortArgument(operation, 'port', documentation=PORT_DOCS)
    argument_table['port'] = arg
    arg = CidrArgument(operation, 'cidr', documentation=CIDR_DOCS)
    argument_table['cidr'] = arg
    arg = SourceGroupArgument(operation, 'source-group',
                              documentation=SOURCEGROUP_DOCS)
    argument_table['source-group'] = arg
    arg = GroupOwnerArgument(operation, 'group-owner',
                             documentation=GROUPOWNER_DOCS)
    argument_table['group-owner'] = arg


class ProtocolArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            try:
                int_value = int(value)
                if int_value < 0 or int_value > 255:
                    msg = ('protocol numbers must be in the range 0-255')
                    raise ValueError(msg)
            except ValueError:
                if value not in ('tcp', 'udp', 'icmp'):
                    msg = ('protocol parameter should be one of: '
                           'tcp|udp|icmp or any valid protocol number.')
                    raise ValueError(msg)
            _build_ip_permissions(parameters, 'IpProtocol', value)


class PortArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        logger.debug('PortArgument value=%s', value)
        if value:
            try:
                if value == '-1' or value == 'all':
                    fromstr = '-1'
                    tostr = '-1'
                elif '-' in value:
                    fromstr, tostr = value.split('-')
                else:
                    fromstr, tostr = (value, value)
                _build_ip_permissions(parameters, 'FromPort', int(fromstr))
                _build_ip_permissions(parameters, 'ToPort', int(tostr))
            except ValueError:
                msg = ('port parameter should be of '
                       'form from[-to] (e.g. 22 or 22-25)')
                raise ValueError(msg)


class CidrArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            value = [{'CidrIp': value}]
            _build_ip_permissions(parameters, 'IpRanges', value)
        

class SourceGroupArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            if value.startswith('sg-'):
                _build_ip_permissions(parameters, 'GroupId', value)
            else:
                _build_ip_permissions(parameters, 'GroupName', value)


class GroupOwnerArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            _build_ip_permissions(parameters, 'UserId', value)
        
                
