#!/bin/sh

echo "start cluster"
vagrant up
while [ $? -ne 0 ]; do
    echo "start cluster"
    vagrant up
done
echo "done"
