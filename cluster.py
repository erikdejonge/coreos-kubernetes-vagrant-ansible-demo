#!/usr/bin/env python
# coding=utf-8
"""
Cluster management tool for setting up a coreos-vagrant cluster
25-02-15: parallel execution of ssh using paramiko
"""

import time
import os
import pickle
import subprocess
import json
import urllib
import socket
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser
from multiprocessing import Pool, cpu_count
from os.path import join, exists, dirname, expanduser

import paramiko
import vagrant


def main():
    """
    main
    """
    if not exists("Vagrantfile"):
        print "== Error: no Vagrantfile in directory =="
        return

    if not exists(".cl"):
        os.mkdir(".cl")

    parser = ArgumentParser(description="Vagrant controller, argument 'all' is whole cluster")
    parser.add_argument("-s", "--ssh", dest="ssh", help="vagrant ssh", nargs='*')
    parser.add_argument("-c", "--command", dest="command", help="execute command on cluster", nargs="*")
    parser.add_argument("-f", "--status", dest="sshconfig", help="status of cluster or when name is given print config of ssh connections", nargs='*')
    parser.add_argument("-u", "--up", dest="up", help="vagrant up")
    parser.add_argument("-d", "--destroy", dest="destroy", help="vagrant destroy -f", action="store_true")
    parser.add_argument("-k", "--halt", dest="halt", help="vagrant halt")
    parser.add_argument("-q", "--provision", dest="provision", help="provision server with playbook (server:playbook)")
    parser.add_argument("-r", "--reload", dest="reload", help="vagrant reload", nargs='*')
    parser.add_argument("-a", "--replacecloudconfig", dest="replacecloudconfig", help="replacecloudconfigs and reboot", action="store_true")
    parser.add_argument("-t", "--token", dest="token", help="print a new token", action="store_true")
    parser.add_argument("-w", "--wait", dest="wait", help="wait between server (-1 == enter)")
    parser.add_argument("-l", "--localizemachine", dest="localizemachine", help="apply specific configuration for a machine", nargs='*')
    parser.add_argument("-p", "--parallel", dest="parallel", help="parallel execution", action="store_true")

    # echo "generate new token"
    options, unknown = parser.parse_known_args()
    provider = None
    vmhostosx = False

    if options.localizemachine is not None:
        options.localizemachine = list(options.localizemachine)

        # noinspection PyTypeChecker
        if len(options.localizemachine) == 0:
            options.localizemachine = 1
        else:
            options.localizemachine = 2

    provider, vmhostosx = localize(options, provider, vmhostosx)

    if options.localizemachine:
        return

    if options.token:
        print_coreos_token_stdout()
    elif options.ssh is not None:
        connect_ssh(options)
    elif options.sshconfig is not None:
        show_config(options)
    elif options.command:
        remote_command(options)
    elif options.up:
        bring_vms_up(options, provider, vmhostosx)
    elif options.destroy:
        destroy_vagrant_cluster()
    elif options.halt:
        haltvagrantcluster(options)
    elif options.provision:
        provision_ansible(options)
    elif options.reload:
        reload_vagrant_cluster(options)
    elif options.replacecloudconfig:
        replace_cloudconfig_coreos_cluster(options, vmhostosx)
    else:
        parser.print_help()


def run_cmd(cmd, pr=False, shell=False, streamoutput=True):
    """
    @type cmd: str, unicode
    @type pr: bool
    @type shell: bool
    @type streamoutput: bool
    @return: None
    """
    if pr:
        print "\033[31mrun_cmd:", cmd, "\033[0m"

    if shell is True:
        return subprocess.call(cmd, shell=True)
    else:
        cmdl = [x for x in cmd.split(" ") if len(x.strip()) > 0]
        p = subprocess.Popen(cmdl, cwd=os.getcwd(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        if streamoutput:
            while p.poll() is None:
                output = p.stdout.readline()
                print "\033[30m", output, "\033[0m",

        out, err = p.communicate()
        if p.returncode != 0:
            print "\033[33m", out, "\033[0m"
            print "\033[31m", err, "\033[0m"
        else:
            if len(out) > 0:
                print "\033[30m", out, "\033[0m"
            else:
                print

    return p.returncode


def get_run_cmd(cmd):
    """
    @type cmd: str, unicode
    @return: None
    """
    cmd = cmd.split(" ")
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = p.communicate()
    out = out.strip()
    err = err.strip()
    if p.returncode != 0:
        print "\033[33m", out, "\033[0m"
        print "\033[31m", err, "\033[0m"

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
        if exists(".cl/vmnames.pickle"):
            l = [x[0] for x in pickle.load(open(".cl/vmnames.pickle"))]
            l.sort()
            return l

        vmnames = []
        numinstances = None

        # noinspection PyBroadException
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

        except Exception, e:
            print "\033[31m", e, "\033[0m"

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
    token = os.popen("curl -s https://discovery.etcd.io/new ").read()
    cnt = 0

    while "Unable" in token:
        if cnt > 3:
            raise AssertionError("could not fetch token")

        time.sleep(1)
        token = os.popen("curl -s https://discovery.etcd.io/new ").read()
        cnt += 1

    return token


def write_config_from_template(ntl, vmhostosx):
    """
    @type ntl: str, unicode
    @type vmhostosx: bool
    @return: None
    """
    node = open(ntl).read()

    if vmhostosx:
        masterip = "192.168.14.41"
        node = node.replace("<master-private-ip>", masterip)
        node = node.replace("<name-node>", "core1.a8.nl")
    else:
        masterip = "192.168.14.51"
        node = node.replace("<master-private-ip>", masterip)
        node = node.replace("<name-node>", "node1.a8.nl")

    print "\033[36mmaster-private-ip:", masterip, "\033[0m"
    config = ntl.replace(".tmpl", "")
    print "\033[36mwriting:", config, "\033[0m"
    open(config, "w").write(node)


def remote_cmd(server, cmd):
    """
    @type server: str, unicode
    @type cmd: str, unicode
    @return: str
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username='core')
    si, so, se = ssh.exec_command(cmd)
    so = so.read()
    se = se.read()

    if len(se) > 0:
        print "\033[31m", se, "\033[0m"

    return so


def remote_cmd_map(servercmd):
    """
    @type servercmd: tuple
    @return: str
    """
    server, cmd = servercmd
    res = remote_cmd(server, cmd)
    return server, res


def scp(server, cmdtype, fp1, fp2):
    """
    @type server: str, unicode
    @type cmdtype: str, unicode
    @type fp1: str, unicode
    @type fp2: str, unicode
    @return: None
    """

    # put back known_hosts file
    run_cmd("ssh -t core@"+server+" date")
    transport = None
    try:
        hostname = server
        port = 22
        username = 'core'
        password = ''
        rsa_private_key = join(os.getcwd(), ".ssh/id_rsa")
        transport = paramiko.Transport((hostname, port))
        transport.start_client()
        ki = paramiko.RSAKey.from_private_key_file(rsa_private_key)
        agent = paramiko.Agent()
        agent_keys = agent.get_keys() + (ki,)

        if len(agent_keys) == 0:
            raise AssertionError("scp: no keys", server)

        authenticated = False

        for key in agent_keys:
            try:
                transport.auth_publickey(username, key)
                authenticated = True
                break
            except paramiko.SSHException:
                pass

        if not authenticated:
            raise AssertionError("scp: not authenticated", server)

        try:
            host_keys = paramiko.util.load_host_keys(expanduser('~/.ssh/known_hosts'))
        except IOError:
            try:
                host_keys = paramiko.util.load_host_keys(expanduser('~/ssh/known_hosts'))
            except IOError:
                print '*** '
                print "\033[31msftp: unable to open host keys file\033[0m"
                host_keys = {}

        if hostname in host_keys:
            hostkeytype = host_keys[hostname].keys()[0]
            hostkey = host_keys[hostname][hostkeytype]

            if not transport.is_authenticated():
                transport.connect(username=username, password=password, hostkey=hostkey)
            else:
                transport.open_session()

            sftp = paramiko.SFTPClient.from_transport(transport)

            if cmdtype == "put":
                sftp.put(fp1, fp2)
            else:
                sftp.get(fp1, fp2)

            return True
    except Exception, e:
        print "\033[31m", '*** Caught exception: %s: %s' % (e.__class__, e), "\033[0m"
    finally:
        if transport is not None:
            transport.close()


def localize(options, provider, vmhostosx):
    """
    @type options: str, unicode
    @type provider: str, unicode
    @type vmhostosx: str, unicode
    @return: None
    """
    if options.destroy is False:
        if options.localizemachine:
            get_run_cmd('rm -Rf ".cl"')
            get_run_cmd('rm -Rf "hosts"')

        if os.popen("uname -a").read().startswith("Darwin"):
            vmhostosx = True

        if options.localizemachine:
            if vmhostosx is True:
                print "\033[33mLocalized for OSX\033[0m"
            else:
                print "\033[33mLocalized for Linux\033[0m"

        if vmhostosx is True:
            provider = "vmware_fusion"

            if exists("./configscripts/setconfigosx.sh") is True:
                os.system("./configscripts/setconfigosx.sh")
        else:
            provider = "vmware_workstation"

            if exists("./configscripts/setconfiglinux.sh"):
                os.system("./configscripts/setconfiglinux.sh")

        if options.localizemachine or options.provision or options.replacecloudconfig:
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
            hosts.write("\n[coreos]\n")

            for name in get_vm_names():
                hosts.write(name + "\n")

            hosts.write("\n[coreos:vars]\n")
            hosts.write("ansible_ssh_user=core\n")
            hosts.write("ansible_python_interpreter=\"PATH=/home/core/bin:/home/core/bin python\"\n")
            hosts.flush()
            hosts.close()

        if options.localizemachine or options.replacecloudconfig or options.reload:
            ntl = "configscripts/node.tmpl.yml"
            write_config_from_template(ntl, vmhostosx)
            ntl = "configscripts/master.tmpl.yml"
            write_config_from_template(ntl, vmhostosx)

            if options.localizemachine == 1:
                p = subprocess.Popen(["/usr/bin/vagrant", "up"], cwd=os.getcwd())
                p.wait()

    return provider, vmhostosx


def connect_ssh(options):
    """
    @type options: str, unicode
    @return: None
    """
    if len(options.ssh) == 1:
        options.ssh = options.ssh[0]
    else:
        options.ssh = 1

    index = None
    try:
        index = int(options.ssh)

        if index <= 0:
            index = 1
    except Exception, e:
        print e

    cnt = 0
    vmnames = get_vm_names()

    if options.ssh not in vmnames:
        for name in vmnames:
            cnt += 1

            if index is None:
                print "\033[36mssh ->", name, "\033[0m"
                cmd = "ssh core@" + name + ".a8.nl"

                while True:
                    try:
                        if run_cmd(cmd, shell=True) != 0:
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
                            if run_cmd(cmd, shell=True) != 0:
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


def show_config(options):
    """
    @type options: str, unicode
    @return: None
    """
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
                    if exists(".cl/" + name + ".sshconfig"):
                        out = open(".cl/" + name + ".sshconfig").read()
                    else:
                        out, eout = get_run_cmd(cmd)

                        if len(eout) == 0:
                            open(".cl/" + name + ".sshconfig", "w").write(out)

                    res = ""

                    for row in out.split("\n"):
                        if "HostName" in row:
                            res = row.replace("HostName", "").strip()

                    result = remote_cmd(name + '.a8.nl', 'cat /etc/os-release|grep VERSION_ID')

                    if len(res.strip()) > 0:
                        print name, res.strip(), "up", result.lower()
                    else:
                        print name, "down"
                except subprocess.CalledProcessError:
                    print name, "down"
        else:
            run_cmd("vagrant status")
    else:
        cmd = "vagrant ssh-config " + options.sshconfig
        run_cmd(cmd)


def print_remote_command_result(result):
    """
    @type result: str, unicode
    @return: None
    """
    if "\n" in result.strip():
        print "\033[37m" + str(result), "\033[0m"
    else:
        print "\033[37m", result, "\033[0m"


def remote_command(options):
    """
    @type options: str, unicode
    @return: None
    """
    server = None

    if len(options.command) == 1:
        options.command = options.command[0]
    elif len(options.command) == 2:
        server = options.command[0]
        options.command = options.command[1]
    else:
        raise AssertionError(options.command)

    if options.parallel is True:
        print "\033[36mremote\033[0m\033[32m parallel\033[0m\033[36m command:\033[0m\033[33m", options.command, "\033[0m"
    else:
        print "\033[36mremote command:\033[0m\033[33m", options.command, "\033[0m"

    if server:
        print "\033[36mon:\033[0m\033[33m", server, "\033[0m"

    print
    if server is None:
        vmnames = get_vm_names()

        if options.command not in vmnames:
            commands = []

            for name in vmnames:
                cmd = options.command

                if options.parallel is True:
                    commands.append((name + '.a8.nl', cmd))
                else:
                    result = remote_cmd(name + '.a8.nl', cmd)

                    if result.strip():
                        print "\033[36mon:\033[0m\033[33m", name, "\033[0m"
                        print_remote_command_result(result)
                    else:
                        print "\033[36mon:\033[0m\033[33m", name, "\033[0m\033[36m... done\033[0m"

                    if options.wait is not None:
                        if str(options.wait) == "-1":
                            try:
                                iquit = raw_input("continue (y/n): ")

                                if iquit.strip() == "n":
                                    break
                            except KeyboardInterrupt:
                                print
                                break
                        else:
                            time.sleep(float(options.wait))

            if len(commands) > 0:
                expool = Pool(cpu_count())

                for server, result in expool.map(remote_cmd_map, commands):
                    if result.strip():
                        print "\033[36mon:\033[0m\033[33m", server.split(".")[0], "\033[0m"
                        print_remote_command_result(result)
                    else:
                        print "\033[36mon:\033[0m\033[33m", server.split(".")[0], "\033[0m\033[36m... done\033[0m"
    else:
        cmd = options.command
        result = remote_cmd(server + '.a8.nl', cmd)

        if result:
            print_remote_command_result(result)
        else:
            print "\033[37m", "done", "\033[0m"


def bring_vms_up(options, provider, vmhostosx):
    """
    @type options: str, unicode
    @type provider: str, unicode
    @type vmhostosx: str, unicode
    @return: None
    """
    if provider is None:
        raise AssertionError("provider is None")

    run_cmd("ssh-add ~/.vagrant.d/insecure_private_key")
    run_cmd("ssh-add ./.ssh/id_rsa;")
    p = subprocess.Popen(["python", "-m", "SimpleHTTPServer", "8000"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
    try:
        numinstances = None
        try:
            numinstances = get_num_instances()
        except Exception, e:
            print "ignored"
            print e

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


def destroy_vagrant_cluster():
    """
    destroy_vagrant_cluster
    """
    cmd = "vagrant destroy  -f"
    run_cmd(cmd)

    if exists(".cl/vmnames.pickle"):
        os.remove(".cl/vmnames.pickle")
        os.system("rm -Rf .cl")

    run_cmd("rm -Rf .vagrant")

    for vmx in os.popen("vmrun list"):
        if ".vmx" in vmx:
            vmx = vmx.strip()
            run_cmd("vmrun stop " + vmx + " > /dev/null &")
            run_cmd("vmrun deleteVM " + vmx + " > /dev/null &")


def haltvagrantcluster(options):
    """
    @type options: str, unicode
    @return: None
    """
    if options.halt == 'all':
        cmd = "vagrant halt"
    else:
        cmd = "vagrant halt " + options.halt

    run_cmd(cmd)


def provision_ansible(options):
    """
    @type options: str, unicode
    @return: None
    """
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

    print "\033[34mAnsible playbook:", playbook, "\033[0m"
    p = subprocess.Popen(["python", "-m", "SimpleHTTPServer", "8000"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
    try:
        if exists("./hosts"):
            vmnames = get_vm_names()

            if targetvmname == "all":
                cmd = "ansible-playbook -u core --inventory-file=" + join(os.getcwd(), "hosts") + " --private-key=vagrantssh/vagrant -u core --extra-vars=\"ansible_python_interpreter='/home/core/bin/python'\" --limit=all " + playbook

                if password is not None:
                    cmd += " --vault-password-file " + f.name
                run_cmd(cmd, shell=True)
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


def reload_vagrant_cluster(options):
    """
    @type options: str, unicode
    @return: None
    """
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


def replace_cloudconfig_coreos_cluster(options, vmhostosx):
    """
    @type options: argparse.Nam
    espace
    @type vmhostosx: str, unicode
    @return: None
    """
    token = get_token()
    print "\033[36mtoken:", token.strip(), "\033[0m"

    if vmhostosx is True:
        open("config/tokenosx.txt", "w").write(token)
    else:
        open("config/tokenlinux.txt", "w").write(token)

    run_cmd("rm -f ./configscripts/user-data*")
    print "\033[31mReplace cloudconfiguration, checking vms are up\033[0m"
    p = subprocess.Popen(["/usr/bin/vagrant", "up"], cwd=os.getcwd())
    p.wait()
    vmnames = get_vm_names()
    knownhosts = join(join(expanduser("~"), ".ssh"), "known_hosts")

    if exists(knownhosts):
        os.remove(knownhosts)

    if len(vmnames) > 0:
        cnt = 1

        for name in vmnames:
            scp(name + '.a8.nl', "put", "configscripts/user-data" + str(cnt) + ".yml", "/tmp/vagrantfile-user-data"),
            cmd = "sudo cp /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/vagrantfile-user-data"
            remote_cmd(name + '.a8.nl', cmd)
            print "\033[37m", name, "uploaded config, rebooting now", "\033[0m"
            if options.wait:
                print "wait: ", options.wait

            logpath = join(os.getcwd(), "logs/" + name + "-serial.txt")

            if exists(dirname(logpath)):
                open(logpath, "w").write("")

            cmd = "sudo reboot"
            remote_cmd(name + '.a8.nl', cmd)

            if options.wait is not None:
                if str(options.wait) == "-1":
                    try:
                        iquit = raw_input("\n\n---\npress enter to continue (q=quit): ")
                        if iquit.strip() == "q":
                            break

                        run_cmd("clear")
                    except KeyboardInterrupt:
                        print
                        break
                else:
                    time.sleep(float(options.wait))

            cnt += 1


def print_coreos_token_stdout():
    """
    print_coreos_token_stdout
    """
    print "\033[36m" + get_token() + "\033[0m"


if __name__ == "__main__":
    main()
