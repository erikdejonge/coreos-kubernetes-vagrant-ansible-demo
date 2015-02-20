#!/bin/sh
echo "destroy old cluster"
read -r -p "Are you sure? [y/N] " response
case $response in
    [yY][eE][sS]|[yY])
        echo "destroying cluster"
        python cluster.py -d all
        rm -Rf .vagrant
        rm -Rf .cl
        rm -f config/user-data*
        killall Python > /dev/null 2> /dev/null
        killall python > /dev/null 2> /dev/null
        ;;
    *)
        echo "better not"
        ;;
esac

