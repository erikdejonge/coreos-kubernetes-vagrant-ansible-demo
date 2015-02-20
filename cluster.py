#!/usr/bin/env python
# coding=utf-8
"""
that cluster
"""

import time
import sys
import os
import pickle
import subprocess
import json
import urllib
import socket
import vagrant
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser


def run_cmd(cmd, pr=False):
    """
    @type cmd: str, unicode
    @type pr: bool
    @return: None
    """

    #pr = True

    if pr:
        # print "-- cwd:", os.getcwd(), "--"
        print cmd
        print "--\n"

    # return
    return os.system(cmd)


def get_run_cmd(cmd):
    """
    @type cmd: str, unicode
    @return: None
    """

    cmd =  cmd.split(" ")
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = p.communicate()
    out = out.strip()
    err = err.strip()
    return out, err


def get_num_instances():
    """
    get_num_instances
    """
    v = open("Vagrantfile").read()
    numinstances = int(v[v.find("num_instances") + (v[v.find("num_instances"):].find("=")):].split("\n")[0].replace("=", "").strip())
    return numinstances


def get_vm_names(retry=False):
    """
    @type retry: str, unicode
    @return: None
    """
    try:
        if os.path.exists(".cl/vmnames.pickle"):
            l = [x[0] for x in pickle.load(open(".cl/vmnames.pickle"))]
            l.sort()
            return l

        vmnames = []
        numinstances = None
        try:
            numinstances = get_num_instances()
            osx = False

            if os.popen("uname -a").read().startswith("Darwin"):
                osx = True

            for i in range(1, numinstances + 1):
                if osx is True:
                    vmnames.append(["core" + str(i), None])
                else:
                    vmnames.append(["node" + str(i), None])

        except:
            pass

        if numinstances is None:
            v = vagrant.Vagrant()
            status = v.status()

            for vm in status:
                vmname = vm.name.split(" ")[0].strip()
                vmnames.append([vmname, v.conf(v.ssh_config(vm_name=vmname))])

        if len(vmnames) > 0:
            pickle.dump(vmnames, open(".cl/vmnames.pickle", "w"))

        l = [x[0] for x in vmnames]
        l.sort()
        return l
    except subprocess.CalledProcessError:
        if retry:
            return []

        return get_vm_names(True)


def get_vm_configs():
    """
    get_vm_configs
    """
    get_vm_names()
    result = [x[1] for x in pickle.load(open(".cl/vmnames.pickle")) if x[1] is not None]

    if len(result) > 0:
        return result
    else:
        v = vagrant.Vagrant()
        status = v.status()
        vmnames = []

        for vm in status:
            vmname = vm.name.split(" ")[0].strip()
            vmnames.append([vmname, v.conf(v.ssh_config(vm_name=vmname))])

        if len(vmnames) > 0:
            pickle.dump(vmnames, open(".cl/vmnames.pickle", "w"))

        return [x[1] for x in vmnames if x[1] is not None]


def get_token():
    """
    get_token
    """
    token = os.popen("curl https://discovery.etcd.io/new  2> /dev/null").read()
    cnt = 0

    while "Unable" in token:
        if cnt > 3:
            raise AssertionError("could not fetch token")

        time.sleep(1)
        token = os.popen("curl https://discovery.etcd.io/new  2> /dev/null").read()
        cnt += 1

    return token


def main():
    """
    main
    """
    if not os.path.exists("Vagrantfile"):
        print "== Error: no Vagrantfile in directory =="
        return

    if not os.path.exists(".cl"):
        os.mkdir(".cl")

    parser = ArgumentParser(description="Vagrant controller, argument 'all' is whole cluster")
    parser.add_argument("-s", "--ssh", dest="ssh", help="vagrant ssh", nargs='*')
    parser.add_argument("-c", "--command", dest="command", help="execute command on cluster", nargs="*")
    parser.add_argument("-f", "--status", dest="sshconfig", help="status of cluster or when name is given print config of ssh connections", nargs='*')
    parser.add_argument("-u", "--up", dest="up", help="vagrant up")
    parser.add_argument("-d", "--destroy", dest="destroy", help="vagrant destroy -f", action="store_true")
    parser.add_argument("-k", "--halt", dest="halt", help="vagrant halt")
    parser.add_argument("-p", "--provision", dest="provision", help="provision server with playbook (server:playbook)")
    parser.add_argument("-q", "--vagrantprovision", dest="vagrantprovision", action="store_true")
    parser.add_argument("-r", "--reload", dest="reload", help="vagrant reload", nargs='*')
    parser.add_argument("-a", "--replacecloudconfig", dest="replacecloudconfig", help="replacecloudconfig /var/lib/coreos-vagrant/vagrantfile-user-data", action="store_true")
    parser.add_argument("-t", "--token", dest="token", help="print a new token", action="store_true")
    parser.add_argument("-n", "--cloudconfig", dest="cloudconfig", help="update cloudconfig (find:replace)")
    parser.add_argument("-w", "--wait", dest="wait", help="wait between server (-1 == enter)")
    parser.add_argument("-l", "--localizemachine", dest="localizemachine", help="apply specific configuration for a machine", nargs='*')

    # echo "generate new token"
    options, unknown = parser.parse_known_args()
    provider = None
    vmhostosx = False

    if options.localizemachine is not None:
        if len(options.localizemachine)==0:
            options.localizemachine = 1
        else:
            options.localizemachine = 2

    if options.destroy is False:
        if options.localizemachine:
            get_run_cmd('rm -Rf ".cl"')
            get_run_cmd('rm -Rf "hosts"')

        if os.popen("uname -a").read().startswith("Darwin"):
            vmhostosx = True

        if options.localizemachine:
            if vmhostosx is True:
                print "Localized for OSX",
            else:
                print "Localized for Linux",

        if vmhostosx is True:
            provider = "vmware_fusion"

            if os.path.exists("./configscripts/setconfigosx.sh") is True:
                os.system("./configscripts/setconfigosx.sh")
        else:
            provider = "vmware_workstation"

            if os.path.exists("./configscripts/setconfiglinux.sh"):
                os.system("./configscripts/setconfiglinux.sh")

        if options.localizemachine or options.provision:
            hosts = open("hosts", "w")

            # for cf in get_vm_configs():
            # hosts.write(cf["Host"] + " ansible_ssh_host=" + cf["HostName"] + " ansible_ssh_port=22\n")
            for name in get_vm_names():
                try:
                    hostip = str(socket.gethostbyname(name + ".a8.nl"))
                    hosts.write(name + " ansible_ssh_host=" + hostip + " ansible_ssh_port=22\n")
                except socket.gaierror:
                    hosts.write(name + " ansible_ssh_host=" + name + ".a8.nl ansible_ssh_port=22\n")

            hosts.write("\n[masters]\n")

            for name in get_vm_names():
                hosts.write(name + "\n")
                break

            cnt = 0
            hosts.write("\n[etcd]\n")

            for name in get_vm_names():
                if cnt == 1:
                    hosts.write(name + "\n")

                cnt += 1

            cnt = 0
            hosts.write("\n[nodes]\n")

            for name in get_vm_names():
                if cnt > 0:
                    hosts.write(name + "\n")

                cnt += 1

            hosts.write("\n[all]\n")

            for name in get_vm_names():
                hosts.write(name + "\n")

            hosts.write("\n[all_groups:children]\nmasters\netcd\nnodes\n")
            hosts.flush()
            hosts.close()

        if options.localizemachine or options.replacecloudconfig or options.reload:
            open("configscripts/master.yml", "w").write(open("configscripts/master.tmpl.yml").read())
            node = open("configscripts/node.tmpl.yml").read()

            if vmhostosx:
                masterip = "192.168.14.41"
                node = node.replace("<master-private-ip>", masterip)
            else:
                masterip = "192.168.14.51"
                node = node.replace("<master-private-ip>", masterip)

            print "masterip:", masterip
            open("configscripts/node.yml", "w").write(node)

            if options.localizemachine == 1:
                os.popen("vagrant up")

            if options.localizemachine:
                return

    if options.token:
        print get_token()
    elif options.ssh is not None:
        if sys.stderr.isatty():
            sys.stderr.write('\x1Bc')
            sys.stderr.flush()

        if len(options.ssh) == 1:
            options.ssh = options.ssh[0]
        else:
            options.ssh = 1

        index = None
        try:
            index = int(options.ssh)

            if index <= 0:
                index = 1
        except:
            pass

        cnt = 0
        vmnames = get_vm_names()

        if options.ssh not in vmnames:
            for name in vmnames:
                cnt += 1

                if index is None:
                    print "ssh ->", name
                    cmd = "ssh core@" + name + ".a8.nl"

                    while True:
                        try:
                            if run_cmd(cmd) != 0:
                                print "connection lost, trying in 1 seconds (ctrl-c to quit)"
                                time.sleep(1)
                            else:
                                break
                        except KeyboardInterrupt:
                            print
                            break

                    if options.ssh != 'all':
                        break
                else:
                    if index == cnt:
                        print "ssh ->", name
                        cmd = "ssh core@" + name + ".a8.nl"

                        while True:
                            try:
                                if run_cmd(cmd) != 0:
                                    print "connection lost, trying in 1 seconds (ctrl-c to quit)"
                                    time.sleep(1)
                                else:
                                    break
                            except KeyboardInterrupt:
                                print
                                break

                        if options.ssh != 'all':
                            break
            else:
                cnt = 0
                print "server", options.ssh, "not found, options are:"
                print

                for name in vmnames:
                    cnt += 1
                    print str(cnt) + ".", name

                print
        else:
            if options.ssh == 'all':
                print "vagrant ssh all is not possible"
            else:
                cmd = "vagrant ssh " + options.ssh
                run_cmd(cmd)

    elif options.sshconfig is not None:
        if len(options.sshconfig) == 1:
            options.sshconfig = options.sshconfig[0]
        else:
            options.sshconfig = "all"

        if options.sshconfig == 'all':
            vmnames = get_vm_names()

            if len(vmnames) > 0:
                for name in vmnames:
                    cmd = "vagrant ssh-config " + name
                    try:
                        out, eout = get_run_cmd(cmd)
                        res = ""

                        for row in out.split("\n"):
                            if "HostName" in row:
                                res = row.replace("HostName", "").strip()

                        if len(res.strip()) > 0:
                            print name, res.strip(), "up"
                        else:
                            print name, "down"
                    except subprocess.CalledProcessError:
                        print name, "down"
            else:
                run_cmd("vagrant status")
        else:
            cmd = "vagrant ssh-config " + options.sshconfig
            run_cmd(cmd)

    elif options.command:
        server = None

        if len(options.command) == 1:
            options.command = options.command[0]
        elif len(options.command) == 2:
            server = options.command[0]
            options.command = options.command[1]
        else:
            print "error", options.command
            return

        print "remote command:", options.command
        if server:
            print "on:", server

        print
        if server is None:
            vmnames = get_vm_names()

            if options.command not in vmnames:
                for name in vmnames:
                    cmd = "ssh -t core@" + name + '.a8.nl ' + options.command
                    result, err = get_run_cmd(cmd)

                    if result:
                        print name + ":\n", result
                    else:
                        print name + ":\n", "done"

                    print
                    if options.wait is not None:
                        if str(options.wait) == "-1":
                            try:
                                quit = raw_input("\n\n---\npress enter to continue (q=quit): ")
                                if quit.strip() == "q":
                                    return

                                run_cmd("clear")
                            except KeyboardInterrupt:
                                print
                                return
                        else:
                            time.sleep(float(options.wait))
        else:
            cmd = "ssh -t core@" + server + '.a8.nl ' + options.command
            result, err = get_run_cmd(cmd)

            if result:
                print server + ":\n", result
            else:
                print server + ":\n", "done"

            print

    elif options.up:
        if provider is None:
            raise AssertionError("provider is None")

        run_cmd("ssh-add ~/.vagrant.d/insecure_private_key")

        p = subprocess.Popen(["python", "-m", "SimpleHTTPServer", "8000"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
        try:
            numinstances = None
            try:
                numinstances = get_num_instances()
            except:
                pass

            allnew = False

            if options.up == 'allnew':
                allnew = True
                options.up = 'all'
                numinstances = None

            if options.up == 'all':
                if numinstances is None:
                    cmd = "vagrant up"

                    if allnew is True:
                        cmd += " --provision"

                    cmd += " --provider=" + provider
                    run_cmd(cmd)
                else:
                    print "bringing up", numinstances, "instances"

                    for i in range(1, numinstances + 1):
                        name = "node" + str(i)

                        if vmhostosx is True:
                            name = "core" + str(i)

                        print name
                        cmd = "vagrant up "
                        cmd += name

                        if allnew is True:
                            cmd += " --provision"

                        cmd += " --provider=" + provider
                        run_cmd(cmd)
            else:
                cmd = "vagrant up " + options.up + " --provider=" + provider
                run_cmd(cmd)
        finally:
            p.kill()

    elif options.destroy:
        cmd = "vagrant destroy  -f"
        run_cmd(cmd)

        if os.path.exists(".cl/vmnames.pickle"):
            os.remove(".cl/vmnames.pickle")
            os.system("rm -Rf .cl")

        run_cmd("rm -Rf .vagrant")

        for vmx in os.popen("vmrun list"):
            if ".vmx" in vmx:
                vmx = vmx.strip()
                run_cmd("vmrun stop " + vmx + " > /dev/null 2> /dev/null &")
                run_cmd("vmrun deleteVM " + vmx + " > /dev/null 2> /dev/null &")

    elif options.halt:
        if options.halt == 'all':
            cmd = "vagrant halt"
        else:
            cmd = "vagrant halt " + options.halt

        run_cmd(cmd)
    elif options.vagrantprovision:
        p = subprocess.Popen(["python", "-m", "SimpleHTTPServer", "8000"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
        try:
            run_cmd("vagrant provision")
        finally:
            p.kill()

    elif options.provision:
        sp = options.provision.split(":")
        password = None
        f = NamedTemporaryFile(delete=False)

        if len(sp) > 2:
            targetvmname, playbook, password = sp
            f.write(password)
            f.seek(0)
        elif len(sp) > 1:
            targetvmname, playbook = sp
        else:
            playbook = sp[0]
            targetvmname = "all"

        p = subprocess.Popen(["python", "-m", "SimpleHTTPServer", "8000"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
        time.sleep(2)
        try:
            if os.path.exists("./hosts"):
                vmnames = get_vm_names()

                if targetvmname == "all":
                    cmd = "ansible-playbook -u core --inventory-file=" + os.path.join(os.getcwd(), "hosts") + " --private-key=vagrantssh/vagrant -u core --extra-vars=\"ansible_python_interpreter='/home/core/bin/python'\" --limit=all " + playbook

                    if password is not None:
                        cmd += " --vault-password-file " + f.name
                    run_cmd(cmd)
                else:
                    for vmname in vmnames:
                        if targetvmname == vmname:
                            print "provisioning", vmname
                            cmd = "ansible-playbook -u core -i ./hosts --private-key=vagrantssh/vagrant -u core --extra-vars=\"ansible_python_interpreter='/home/core/bin/python'\" --limit=" + vmname + " " + playbook

                            if password is not None:
                                cmd += " --vault-password-file " + f.name

                            print cmd
                            run_cmd(cmd)
                        else:
                            print "skipping", vmname
            else:
                run_cmd("vagrant provision")
        finally:
            p.kill()
            os.remove(f.name)

    elif options.reload:
        if len(options.reload) == 1:
            options.reload = options.reload[0]
        else:
            options.reload = "all"

        if options.reload == "all":
            print "reloading all"
            run_cmd("vagrant reload")
        else:
            print "stop and start", options.reload
            run_cmd("vagrant halt -f " + str(options.reload))
            run_cmd("vagrant up " + str(options.reload))

    elif options.replacecloudconfig:
        token = get_token()
        print "token:", token
        if vmhostosx is True:
            open("config/tokenosx.txt", "w").write(token)
        else:
            open("config/tokenlinux.txt", "w").write(token)

        run_cmd("rm -f ./configscripts/user-data* 2> /dev/null")
        print "Replace cloudconfiguration, checking vms are up"
        run_cmd("vagrant up > /dev/null")
        run_cmd("rm -f ~/.ssh/known_hosts > /dev/null 2> /dev/null")
        vmnames = get_vm_names()
        found = False

        if len(vmnames) > 0:
            cnt = 1

            for name in vmnames:
                print name, "upload config",
                sys.stdout.flush()
                cmd = "ssh -t core@" + name + ".a8.nl date > /dev/null 2> /dev/null"
                run_cmd(cmd)
                cmd = "scp configscripts/user-data" + str(cnt) + ".yml core@" + name + ".a8.nl:/tmp/vagrantfile-user-data"
                out, err = get_run_cmd(cmd)

                if len(err) > 0:
                    raise AssertionError(err)

                cmd = "sudo cp /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/vagrantfile-user-data"
                cmd = "ssh -t core@" + name + ".a8.nl \"" + cmd + '" 2> /dev/null'
                run_cmd(cmd)
                print "done, rebooting now"
                if options.wait:
                    print "wait: ", options.wait

                cmd = "ssh -t core@" + name + ".a8.nl \"sudo reboot\" 2> /dev/null"
                run_cmd(cmd)

                if options.wait is not None:
                    if str(options.wait) == "-1":
                        try:
                            quit = raw_input("\n\n---\npress enter to continue (q=quit): ")
                            if quit.strip() == "q":
                                break

                            run_cmd("clear")
                        except KeyboardInterrupt:
                            print
                            return
                    else:
                        time.sleep(float(options.wait))

                cnt += 1

    elif options.cloudconfig:
        sp = options.cloudconfig.split(":")
        if len(sp) != 2:
            print "cloudconfig needs 2 params (find:replace)"
            return
        else:
            find, replace = sp
            print 'replacing cloudconfig with:'
            print "find:", find
            print "replace:", replace
            print

        vmnames = get_vm_names()
        cloudconfigpath = "/var/lib/coreos-vagrant/vagrantfile-user-data"
        cloudconfig = os.path.basename(cloudconfigpath)

        if len(vmnames) > 0:
            for name in vmnames:
                run_cmd("scp -q core@" + name + ".a8.nl:" + cloudconfigpath + " .")
                ncf = open(cloudconfig).read()
                ncf = ncf.replace(find, replace)
                open(cloudconfig, "w").write(ncf)
                run_cmd("scp -q " + cloudconfig + " core@" + name + ".a8.nl:" + cloudconfigpath)
                os.remove(cloudconfig)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
