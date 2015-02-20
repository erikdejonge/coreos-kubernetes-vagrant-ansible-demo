#!/bin/sh
python cluster.py -n "Gateway=192.168.14.1:Gateway=""$(< config/gateway.txt)"
python cluster.py -n "Gateway=192.168.14.254:Gateway=""$(< config/gateway.txt)"
python cluster.py -c "sudo coreos-cloudinit --from-file=/var/lib/coreos-vagrant/vagrantfile-user-data"
python cluster.py -p all:./playbooks/reboot.yml
