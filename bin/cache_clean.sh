#!/bin/bash

#
# cache_clean.sh
# Cron script for maintaining the loris cache size.
#
# CAUTION - This script deletes files. Be careful where you point it!
#
# @author <jstroop@princeton.edu>
#

# Check that the cache directory
CACHE_DIR="/tmp/loris_test/cache"

# is below a certain size (in KB)
# MAX_SIZE=524288000 #500 gb in kb
REDUCE_TO=3072 #3 mb in kb

# and when it is larger, start deleting files accessed more than a certain 
# number of days ago until the cache is smaller than the configured size.

# Note the name of the variable _REDUCE_TO_: this should not be the total 
# amount of space  you can afford for the cache, but instead the total space 
# you can afford MINUS the amount you expect the cache to grow in between 
# executions of this script.

current_usage () {
	echo $(du -sk $CACHE_DIR | cut -f 1)
}

max_age=60 # days
usage=$(current_usage)
while [ $usage -gt $REDUCE_TO ] && [ $max_age -ge -1 ]; do
	echo $max_age
	echo $usage

	# files.
	find $CACHE_DIR -type f -atime +$max_age -delete

	# broken symlinks
	find -L $CACHE_DIR -type l -delete
	
	# empty directories
	find $CACHE_DIR -mindepth 1 -type d -empty -delete

	let max_age-=1
	usage=$(current_usage)
done


