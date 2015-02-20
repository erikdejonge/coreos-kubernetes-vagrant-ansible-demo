#!/bin/sh
#/bin/bash

set -e

cd

if [-e $HOME/.bootstrapped]; then
  exit 0
fi

PYPY_VERSION=2.4.0

wget http://192.168.14.12:8000/roles/coreos-bootstrap/files/pypy-2.4.0-linux64.tar.gz

tar -xf pypy-2.4.0-linux64.tar.gz
mv pypy-$PYPY_VERSION-linux64 pypy

## library fixup
if [ ! -d "pypy/lib" ]; then
  mkdir pypy/lib
fi
ln -s /lib64/libncurses.so.5.9 $HOME/pypy/lib/libtinfo.so.5

if [ ! -d "$HOME/bin" ]; then
  mkdir -p $HOME/bin
fi

cat > $HOME/bin/python <<EOF
#!/bin/bash
LD_LIBRARY_PATH=$HOME/pypy/lib:$LD_LIBRARY_PATH $HOME/pypy/bin/pypy "\$@"
EOF

chmod +x $HOME/bin/python
$HOME/bin/python --version

rm -f pypy-$PYPY_VERSION-linux64.tar.bz2
