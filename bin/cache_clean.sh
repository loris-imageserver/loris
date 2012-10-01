#!/bin/bash

#
# cache_clean.sh
# Cron script for maintaining the loris cache size.
#
# @author <jstroop@princeton.edu>
#

# Checks that the cache directory
CACHE_DIR='/tmp/loris_test/cache'

# is below a configurable maximum size (in KB)
# MAX_SIZE=524288000 #500 gb in kb
MAX_SIZE=3072 #3 mb in kb

current_usage () {
	echo $(du -sk $CACHE_DIR | cut -f 1)
}

# and when it is larger, starts deleting files older than a certain number 
# of days until the cache is smaller than the maximum size



max_age=60
usage=$(current_usage)
while [ $usage -gt $MAX_SIZE ] && [ $max_age -ge -1 ]; do
	echo $max_age
	echo $usage
	echo ''

	files=$(find $CACHE_DIR -type f -mtime +$max_age)
	# ideally we'd like to pop files off of the array one at a time until 
	# there we're under $MAX_SIZE 

	let max_age-=1
	usage=$(current_usage)
done
