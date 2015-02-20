#!/bin/sh
cat ./roles/coreos-bootstrap/files/bootstraposx.txt > ./roles/coreos-bootstrap/files/bootstrap.sh

echo "192.168.14.4" > ./config/startip.txt
echo "core" > ./config/basehostname.txt

cat ./config/tokenosx.txt > ./config/token.txt

sed -e 's/$num_instances = x/$num_instances = 3/g' Vagrantfile.tpl.rb > Vagrantfile
sed -i 's/node/core/g' Vagrantfile
sed -i 's/core.yml/node.yml/g' Vagrantfile
sed -i 's/$vm_gui = false/$vm_gui = true/g' Vagrantfile
sed -i 's/$vm_cpus = x/$vm_cpus = 2/g' Vagrantfile
sed -i 's/$vm_memory = x/$vm_memory = 1024/g' Vagrantfile
sed -i "s/$update_channel = 'beta'/$update_channel = 'beta'/g" Vagrantfile

