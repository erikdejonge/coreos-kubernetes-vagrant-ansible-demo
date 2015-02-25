# -*- mode: ruby -*-
# # vi: set ft=ruby :
require 'fileutils'
require 'open-uri'
require 'yaml'
Vagrant.require_version '>= 1.6.0'
$cloud_config_path = ""
# Defaults for config options defined in CONFIG
$num_instances = x
$update_channel = 'beta'
$enable_serial_logging = false
$share_home = false
$vm_gui = false
$vm_memory = x
$vm_cpus = x
$etcdaddress = nil
# Attempt to apply the deprecated environment variable NUM_INSTANCES to
# $num_instances while allowing config.rb to override it
if ENV['NUM_INSTANCES'].to_i > 0 && ENV['NUM_INSTANCES']
    $num_instances = ENV['NUM_INSTANCES'].to_i
end
# Use old vb_xxx config variables when set
def vm_gui
    $vb_gui.nil? ? $vm_gui : $vb_gui
end

def vm_memory
    $vb_memory.nil? ? $vm_memory : $vb_memory
end

def vm_cpus
    $vb_cpus.nil? ? $vm_cpus : $vb_cpus
end

Vagrant.configure('2') do |config|
    config.ssh.insert_key = false
    config.ssh.private_key_path = ['vagrantssh/vagrant']
    config.vm.box = 'coreos-%s' % $update_channel
    config.vm.box_version = '>= 308.0.1'
    config.vm.box_url = "http://%s.release.core-os.net/amd64-usr/current/coreos_production_vagrant.json" % $update_channel
    ["vmware_fusion", "vmware_workstation"].each do |vmware|
        config.vm.provider vmware do |v, override|
            override.vm.box_url = "http://%s.release.core-os.net/amd64-usr/current/coreos_production_vagrant_vmware_fusion.json" % $update_channel
        end
    end
    config.vm.provider :virtualbox do |v|
        # On VirtualBox, we don't have guest additions or a functional vboxsf
        # in CoreOS, so tell Vagrant that so it can be smarter.
        v.check_guest_additions = false
        v.functional_vboxsf = false
    end
    # plugin conflict
    if Vagrant.has_plugin?('vagrant-vbguest') then
        config.vbguest.auto_update = false
    end
    (1..$num_instances).each do |i|
        basehostname = open("config/basehostname.txt").read
        basehostname = basehostname.strip
        basehostname = basehostname+ '%1d' % i
        config.vm.define vm_name = basehostname do |config|
            config.vm.hostname = vm_name+".a8.nl"
            #if $expose_docker_tcp
            #    config.vm.network 'forwarded_port', guest: 2375, host: ($expose_docker_tcp + i - 1), auto_correct: true
            #end
            logdir = File.join(File.dirname(__FILE__), "logs")
            FileUtils.mkdir_p(logdir)

            serialFile = File.join(logdir, "%s-serial.txt" % vm_name)
            FileUtils.touch(serialFile)
            ['vmware_fusion', 'vmware_workstation'].each do |vmware|
                config.vm.provider vmware do |v|
                    v.gui = vm_gui
                    v.vmx['memsize'] = vm_memory
                    v.vmx['numvcpus'] = vm_cpus
                    v.vmx["serial0.present"] = "TRUE"
                    v.vmx["serial0.fileType"] = "file"
                    v.vmx["serial0.fileName"] = serialFile
                    v.vmx["serial0.tryNoRxLoss"] = "FALSE"

                end
            end
            config.vm.provider :virtualbox do |vb|
                vb.gui = vm_gui
                vb.memory = vm_memory
                vb.cpus = vm_cpus
            end
            startip = open("config/startip.txt").read
            startip = startip.strip
            pubipaddress = startip + "%1d" % i
            if $etcdaddress==nil
                $etcdaddress = pubipaddress
            end
            config.vm.network :public_network, ip: pubipaddress
            if ARGV[0].eql?('up')
                $cloud_config_path = File.join(File.dirname(__FILE__), 'configscripts/user-data%1d' % i)
                $cloud_config_path += ".yml"
                token = open("config/token.txt").read
                token = token.strip
                privipaddress = "127.0.0.1"
                updategroup = open("config/updatetoken.txt").read
                updategroup = updategroup.strip
                if i==1
                    data = YAML.load(IO.readlines('configscripts/master.yml')[1..-1].join)
                else
                    data = YAML.load(IO.readlines('configscripts/node.yml')[1..-1].join)
                end
                data['coreos']['update']['group'] = updategroup
                gateway = open('config/gateway.txt').read
                environ = 'COREOS_PUBLIC_IPV4='+pubipaddress+"\nCOREOS_PRIVATE_IPV4="+privipaddress
                envvars = open('config/envvars.sh').read
                envvars = envvars.strip + "\n"
                envvars += "export ETCDCTL_PEERS='http://"+$etcdaddress+":4001'\n"
                envvars += "export FLEETCTL_ENDPOINT='http://"+$etcdaddress+":4001'\n"
                envvars += "export DEFAULT_IPV4='"+pubipaddress+"'\n\n"
                data['write_files'][0]['content'] = "[Match]\nName=ens34\n\n[Network]\nAddress="+pubipaddress+"/24\nGateway="+gateway+"\nDNS=8.8.8.8\nDNS=8.8.4.4\n\n"
                data['write_files'][1]['content'] = environ
                data['write_files'][2]['content'] = envvars
                data['hostname'] = configvm.vm.hostname
                yaml = YAML.dump(data)
                yaml = yaml.gsub("\\{", "{")
                File.open($cloud_config_path, 'w') { |file| file.write("#cloud-config\n\n#{yaml}\n\n") }
            end
            # Uncomment below to enable NFS for sharing the host machine into the coreos-vagrant VM.
            #config.vm.synced_folder ".", "/home/core/share", id: "core", :nfs => true, :mount_options => ['nolock,vers=3,udp']
            if $share_home
                config.vm.synced_folder ENV['HOME'], ENV['HOME'], id: 'home', :nfs => true, :mount_options => ['nolock,vers=3,udp']
            end
            if File.exist?($cloud_config_path)
                config.vm.provision :file, :source => "#{$cloud_config_path}", :destination => "/tmp/vagrantfile-user-data"
                config.vm.provision :shell, :inline => "mv /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/vagrantfile-user-data", :privileged => true
                config.vm.provision :shell, :inline => "halt -p", :privileged => true
            end
            #
            # config.vm.provision 'ansible' do |ansible|
            #     #     ansible.playbook = 'playbook.yml'
            #     ansible.playbook = 'playbooks/ansiblebootstrap.yml'
            #     ansible.limit = 'all'
            #     ansible.extra_vars = {ansible_python_interpreter: 'PATH=/home/core/bin:$PATH python'}
            # end
            #config.vm.provision :reload
        end
    end
end
