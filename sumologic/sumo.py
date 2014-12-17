#!/usr/bin/python

import platform
import os
import shutil

class Sumo(object):

    def __new__(cls, *args, **kwargs):
        return load_platform_subclass(Sumo, args, kwargs)

    def __init__(self, module):
        self.module     = module
        self.changed    = False
        self.state      = module.params['state']
        self.err        = ""
        self.out        = ""

    def is_installed(self):
        return self.is_installed()

    def install(self):
        return self.install()

    def uninstall(self):
        return self.uninstall()


class WindowsSumo(Sumo):
    platform = 'Windows'
    distribution = None

    def is_installed(self):
        if os.path.exists("C:\sumo"):
            return True
        else:
            return False



class LinuxSumo(Sumo):
    platform = 'Linux'
    distribution = None

    def is_installed(self):
        if os.path.exists("/opt/SumoCollector/collector"):
            return True
        else:
            return False

    def install(self):
        if self.is_installed():
            # nothing to do
            self.changed = False
        else:
            # do the install
            if platform.machine() == 'i386': # 32-bit
                rc, out, err = self.module.run_command("curl https://collectors.sumologic.com/rest/download/linux/32 -O;chmod +x 32;bash 32 -q")
                #os.system("curl https://collectors.sumologic.com/rest/download/linux/32 | bash /dev/stdin -q")
            elif platform.machine() == 'x86_64': # 64-bit
                rc, out, err = self.module.run_command("curl https://collectors.sumologic.com/rest/download/linux/64 -o /tmp/sumo-install.sh")
                rc, out, err = self.module.run_command("chmod +x /tmp/sumo-install.sh")
                rc, out, err = self.module.run_command("bash /tmp/sumo-install.sh -q")
                self.changed = True
                self.out = out
                self.err = err
                self.module.run_command("rm -f /tmp/sumo-install.sh")

                #os.system("curl -s https://collectors.sumologic.com/rest/download/linux/64 | bash /dev/stdin -q")


    def uninstall(self):
        if not self.is_installed():
            # nothing to do
            self.changed = False
        else:
            # do the uninstall
            rc, out, err = self.module.run_command("/bin/bash /opt/SumoCollector/uninstall -q")
            #os.system("/bin/bash /opt/SumoCollector/uninstall -q")
            #shutil.rmtree("/opt/SumoCollector/")
            self.changed = True



def main():

    module = AnsibleModule(
        argument_spec = dict(
            state = dict(required=True, choices=['present', 'absent'], type='str')
        ),
        supports_check_mode=False
    )

    sumo = Sumo(module)
    result = {}
    result['changed'] = False

    try:

        if sumo.state == 'present':
            result['do_install'] = "yes"
            sumo.install()
        elif sumo.state == 'absent':
            sumo.uninstall()

        result['changed'] = sumo.changed
        result['out'] = sumo.out
        result['err'] = sumo.err

        module.exit_json(**result)

    except RuntimeError as e:
        module.fail_json(msg=e)


# import module snippets
from ansible.module_utils.basic import *
main()
