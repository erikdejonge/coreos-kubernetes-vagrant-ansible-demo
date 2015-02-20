#!/bin/sh

cat ./roles/coreos-bootstrap/files/bootstraplinux.txt > ./roles/coreos-bootstrap/files/bootstrap.sh
echo "192.168.14.5" > ./config/startip.txt
echo "node" > ./config/basehostname.txt
cat ./config/tokenlinux.txt > ./config/token.txt

sed -e 's/$num_instances = x/$num_instances = 5/g' Vagrantfile.tpl.rb > Vagrantfile
sed -i 's/$vm_gui = false/$vm_gui = false/g' Vagrantfile
sed -i 's/$vm_cpus = x/$vm_cpus = 2/g' Vagrantfile
sed -i 's/$vm_memory = x/$vm_memory = 2038/g' Vagrantfile
sed -i "s/$update_channel = 'beta'/$update_channel = 'beta'/g" Vagrantfile

