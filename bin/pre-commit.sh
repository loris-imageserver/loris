#!/bin/sh

# stash unstaged changes
git stash -q --keep-index

# run tests
python -m unittest -vf test.suite
RESULT=$?

# bring back unstaged changes
git stash pop -q

[ $RESULT -ne 0 ] && exit 1
exit 0
