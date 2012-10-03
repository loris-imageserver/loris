#!/bin/sh
git stash -q --keep-index

# run tests
python -m unittest -vf tests
RESULT=$?

git stash pop -q

[ $RESULT -ne 0 ] && exit 1
exit 0
