#!/usr/bin/python
#
# This is a free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This Ansible library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: s3_website_redirect_rule
short_description: Configure an s3 bucket website redirect rule
description:
    - Configure an s3 bucket website redirect rule
version_added: "2.0"
author: Rob White, wimnat [at] gmail.com, @wimnat
options:
  name:
    description:
      - s3 bucket name
    required: true
    default: null 
  key_prefix:
    description:
      - The object key name prefix from which requests will be redirected.
    required: false
    default: null
  http_error_code:
    description:
      - The HTTP error code that must match for the redirect to apply. In the event of an error, if the error code meets this value, then specified redirect applies.
    required: false
  protocol:
    description:
      - The protocol, http or https, to be used in the Location header that is returned in the response.
    required: false
    default: null
    choices: [ 'http', 'https' ]
  hostname:
    description:
      - The hostname to be used in the Location header that is returned in the response.
    required: false
    default: null
  replace_key_prefix_with:
    description:
      - The object key name prefix that will replace the value of key_prefix in the redirect request.
    required: false
    default: null
  replace_key_with:
    description:
      - The object key to be used in the Location header that is returned in the response.
    required: false
    default: null
  http_redirect_code:
    description:
      - The HTTP redirect code to be used in the Location header that is returned in the response.
    default: null
  state:
    description:
      - Add or remove s3 website redirect rule
    required: false
    default: present
    
extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.

# Configure an s3 bucket to redirect all requests from mybucket.com/here to example.com
- s3_website_redirect_rule:
    name: mybucket.com
    key_prefix: /here
    hostname: example.com
    state: present
    

    
'''

import xml.etree.ElementTree as ET

try:
    import boto.ec2
    from boto.s3.connection import OrdinaryCallingFormat
    from boto.s3.website import RedirectLocation, RoutingRules, RoutingRule, Redirect, Condition
    from boto.exception import BotoServerError, S3CreateError, S3ResponseError
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


def get_error_message(xml_string):

    root = ET.fromstring(xml_string)
    for message in root.findall('.//Message'):
        return message.text

def get_error_code(xml_string):

    root = ET.fromstring(xml_string)
    for message in root.findall('.//Code'):
        return message.text


def get_website_redirect_conf_plus(bucket):
    
    website_config = bucket.get_website_configuration()
    website_redirect_config = website_config.WebsiteConfiguration.RoutingRules
    return website_redirect_config
            
def create_redirect_rule(connection, module):
    
    name = module.params.get("name")
    key_prefix = module.params.get("key_prefix")
    http_error_code = module.params.get("http_error_code")
    protocol = module.params.get("protocol")
    hostname = module.params.get("hostname")
    replace_key_prefix_with = module.params.get("replace_key_prefix_with")
    replace_key_with = module.params.get("replace_key_with")
    http_redirect_code = module.params.get("http_redirect_code")
    changed = False
    
    # Check bucket exists
    try:
        bucket = connection.get_bucket(name)
    except S3ResponseError, e:
        module.fail_json(msg=str(get_error_message(e.args[2])))
        
    # Check bucket is configured as website
    try:
        website_config = bucket.get_website_configuration_obj()
    except S3ResponseError, e:
        module.fail_json(msg=str(get_error_message(e.args[2])))
        
    current_redirect_rules = website_config.routing_rules
    
    # Create routing rules object
    routing_rules_obj = RoutingRules()
    
    # Create redirect rule
    rule = RoutingRule.when(key_prefix=key_prefix, http_error_code=http_error_code).then_redirect(hostname, protocol, replace_key_with, replace_key_prefix_with, http_redirect_code)

    appended = False
    for existing_rule in current_redirect_rules:
        # Match based on http_error_code and prefix
        if rule.condition.http_error_code == existing_rule.condition.http_error_code and rule.condition.key_prefix == existing_rule.condition.key_prefix:
            if rule.to_xml() == existing_rule.to_xml():
                # append the already existing rule (no change)
                routing_rules_obj.add_rule(rule)
                appended = True
            else:
                # replace the existing rule
                routing_rules_obj.add_rule(rule)
                appended = True
                changed = True
        else:
            routing_rules_obj.add_rule(existing_rule)
    
    if not appended:
        routing_rules_obj.add_rule(rule)
        changed = True
        
    try:
        bucket.configure_website(website_config.suffix, website_config.error_key, website_config.redirect_all_requests_to, routing_rules_obj)
    except BotoServerError, e:
        module.fail_json(msg=str(get_error_message(e.args[2])))
        
    module.exit_json(changed=changed, config=get_website_redirect_conf_plus(bucket))
        
    
    
def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            name = dict(required=True, default=None),
            key_prefix = dict(required=False, default=None),
            http_error_code = dict(required=False, default=None),
            protocol = dict(required=False, default=None),
            hostname = dict(required=False, default=None),
            replace_key_prefix_with = dict(required=False, default=None),
            replace_key_with = dict(required=False, default=None),
            http_redirect_code = dict(required=False, default=None),
            state = dict(default='present', choices=['present', 'absent'])
        )
    )
    
    module = AnsibleModule(argument_spec=argument_spec,
                           required_one_of = [ ['key_prefix', 'http_error_code'] ]
                           )

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')
    
    region, ec2_url, aws_connect_params = get_aws_connection_info(module)

    if region:
        try:
            connection = connect_to_aws(boto.s3, region, **aws_connect_params)
        except (boto.exception.NoAuthHandlerFound, StandardError), e:
            module.fail_json(msg=str(e))
    else:
        module.fail_json(msg="region must be specified")

    state = module.params.get("state")

    if state == 'present':
        create_redirect_rule(connection, module)
    elif state == 'absent':
        destroy_redirect_rule(connection, module)


from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>

main()
