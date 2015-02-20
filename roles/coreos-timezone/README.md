coreos-timezone
===============

[![Ansible Galaxy](https://img.shields.io/badge/galaxy-mkaag.coreos--timezone-660198.svg)](https://galaxy.ansible.com/list#/roles/2572)

Ansible role for setting timezone on CoreOS.

Requirements
------------

Install [Ansible](http://www.ansible.com) on your computer, refer to the official [documentation](http://docs.ansible.com/intro_installation.html) for more details.

Installation
------------

`ansible-galaxy install mkaag.coreos-timezone`

Role Variables
--------------

The variable **coreos_timezone** is defined in the file **defaults/main.yml**. 
It must be a valid entry from the system as defined in the folder **/usr/share/zoneinfo**.

Dependencies
------------

None

Example Playbook
----------------

```yml
---
- hosts: coreos
  sudo: true
  vars:
    coreos_timezone: 'Europe/Zurich'
  roles:
    - mkaag.coreos-timezone
```

License
-------

MIT