#CoreOS-Kubernetes-Vagrant-Ansible-demo
Test setup to run a kubernetes cluster locally with Vagrant and the VMware plugin, Ansible is also initialized for CoreOS.

Based on:
[Deploying Kubernetes on CoreOS with Fleet and Flannel](https://github.com/kelseyhightower/kubernetes-fleet-tutorial)

Ansible integration with:
[Ansible-coreos-bootstrap](https://github.com/defunctzombie/ansible-coreos-bootstrap)


####Requirements
* [VMware Fusion 7.0](http://www.vmware.com/products/fusion/fusion-evaluation)
* [Vagrant](https://www.Vagrantup.com)
    * [Vagrant VMware plugin](http://www.vagrantup.com/VMware)
* python
    * pip install Vagrant


####Initial setup
Find replace 'myusername' with the current username
```bash
sed -i 's/myusername/'`whoami`'/g' ./configscripts/master.tmpl.yml
sed -i 's/myusername/'`whoami`'/g' ./configscripts/node.tmpl.yml
```
Set gateway in ./config/gateway.txt
```bash
# on osx
netstat -nr | awk 'NR>4'| awk 'NR<2' | awk '{print $2}' > ./config/gateway.txt
```


####CloudConfig
Most customizations are done with [Cloud-Config](https://coreos.com/docs/cluster-management/setup/cloudinit-cloud-config/), sinces the kubernetes master is different from the nodes two templates are used, [master](./configscripts/master.tmpl.yml) and [node](./configscripts/node.tmpl.yml).

The VM will be configured by a ["user-dateN.yml"](./configscripts/user-data1.yml) file, this gets generated by cluster.py and Vagrant.

Extra aliases can be added in [envvars.sh](./config/envvars.sh)

####Start cluster
The 'createcluster.sh' script initializes the vm's and runs the initial Ansible playbooks.

```bash
./createcluster.sh
```

####Cluster tool
After the cluster is up you can use the clustertool to run task, most common are:

######Connect to a server
```bash
# connect to core1
python cluster.py -s core1

# connect to 1
python cluster.py -s 3
```

######Run commands on all the servers
```bash
python cluster.py -c "date"
remote command: date

core1:
Fri Feb 20 10:27:28 CET 2015

core2:
Fri Feb 20 10:27:28 CET 2015

core3:
Fri Feb 20 10:27:28 CET 2015
```

######Run Ansible playbooks
```bash
python cluster.py -p all:./playbooks/testAnsible.yml
```

######Show config
```bash
python cluster.py -p
```

######Replace the Cloud-Config files on all servers
```bash
# ./configscripts/master.tmpl.yml -> ./configscripts/user-data1.yml
# ./configscripts/node.tmpl.yml -> ./configscripts/user-data2-n.yml
python cluster.py -a
```

######All arguments
```bash
Vagrant controller, argument 'all' is whole cluster

optional arguments:
  -h, --help            show this help message and exit
  -s [SSH [SSH ...]], --ssh [SSH [SSH ...]]
                        Vagrant ssh
  -c [COMMAND [COMMAND ...]], --command [COMMAND [COMMAND ...]]
                        execute command on cluster
  -u UP, --up UP        Vagrant up
  -d, --destroy         Vagrant destroy -f
  -k HALT, --halt HALT  Vagrant halt
  -q, --Vagrantprovision
  -r [RELOAD [RELOAD ...]], --reload [RELOAD [RELOAD ...]]
                        Vagrant reload
  -t, --token           print a new token
  -n CLOUDCONFIG, --cloudconfig CLOUDCONFIG
                        update cloudconfig (find:replace)
  -w WAIT, --wait WAIT  wait between server (-1 == enter)
  -l [LOCALIZEMACHINE [LOCALIZEMACHINE ...]], --localizemachine [LOCALIZEMACHINE [LOCALIZEMACHINE ...]]
                        apply specific configuration for a machine
```

####Delete cluster
To delete everything

```bash
./deletecluster.sh
```

####Example
From the [Kubernetes guestbook example](https://github.com/GoogleCloudPlatform/kubernetes/tree/master/examples/guestbook)

######.kubeconfig
```yaml
apiVersion: v1
clusters:
- cluster:
    api-version: v1beta2
    server: http://core1.a8.nl:8080
  name: test-cluster-mac
```

[build kubernetes here, for the kubectl app](https://github.com/GoogleCloudPlatform/kubernetes/tree/master/build)

```bash
$ cluster/kubectl.sh --kubeconfig="./.kubeconfig" config view
current-context: ""
Running: cluster/../cluster/gce/../../_output/local/bin/darwin/amd64/kubectl --kubeconfig=./.kubeconfig config view
clusters:
  test-cluster-linux:
    api-version: v1beta2
    server: http://node1.a8.nl:8080
  test-cluster-mac:
    api-version: v1beta2
    server: http://core1.a8.nl:8080
contexts: {}
current-context: ""
preferences: {}
users: {}
$ cluster/kubectl.sh --kubeconfig="./.kubeconfig" --cluster="test-cluster-mac" create -f ./guestbook/redis-master-service.yaml ^C
$ cluster/kubectl.sh --kubeconfig="./.kubeconfig" --cluster="test-cluster-mac" get services
current-context: ""
Running: cluster/../cluster/gce/../../_output/local/bin/darwin/amd64/kubectl --kubeconfig=./.kubeconfig --cluster=test-cluster-mac get services
NAME                LABELS                                    SELECTOR            IP                  PORT
kubernetes          component=apiserver,provider=kubernetes   <none>              10.100.0.2          443
kubernetes-ro       component=apiserver,provider=kubernetes   <none>              10.100.0.1          80
redis-master        name=redis-master                         name=redis-master   10.100.90.132       6379
```
