#!/bin/sh
sudo clear

rm -f hosts
rm -f ./configscripts/user-data*

if [ -d ".vagrant" ]; then
  echo "[./.vagrant] directory still exsists (run ./deletecluster.sh?)"
  exit
fi

echo "preparing start"
rm -Rf .cl
python cluster.py -l allnew
while [ $? -ne 0 ]; do
    python cluster.py -l allnew
done

echo "Update vagrant image"
vagrant box update

echo 'request coreos token'
if [ "$(uname)" == "Darwin" ]; then
  python cluster.py -t > config/tokenosx.txt

  sudo vmnet-cli --stop
  sleep 1
  sudo vmnet-cli --start
  sleep 2
  sudo vmnet-cli --status
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  python cluster.py -t > config/tokenlinux.txt
  sudo /usr/bin/vmware-networks --stop
  sleep 1
  sudo /usr/bin/vmware-networks --start
  sleep 1
fi

echo "Bring machines up"
rm -f ~/.ssh/known_hosts
vagrant up --provision

vagrant up
while [ $? -ne 0 ]; do
    echo "** vagrant up"
    vagrant up
done

echo "Add keys"
ssh-add ~/.vagrant.d/insecure_private_key

echo "Python and pip"
python cluster.py -p all:./playbooks/ansiblebootstrap.yml
python cluster.py -p all:./playbooks/testansible.yml
python cluster.py -p all:./playbooks/containersloading.yml

#echo "Provision containers"
#python cluster.py -p all:./playbooks/containersloading.yml:pi3eneki

killall Python > /dev/null 2> /dev/null
killall python > /dev/null 2> /dev/null

echo "Restart cluster with new token"
python cluster.py -a

echo "Done"



#vagrant halt -f
#vagrant up
#python cluster.py -c "date"


