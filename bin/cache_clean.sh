#!/bin/bash

#
# cache_clean.sh
# Cron script for maintaining the loris cache size.
#
# CAUTION - This script deletes files. Be careful where you point it!
#
# @author <jstroop@princeton.edu>
#
LOG="/tmp/loris_test/cache_clean.log"
# Check that the cache directory
CACHE_DIR="/tmp/loris_test/cache"

# is below a certain size (in KB)
# REDUCE_TO=524288000 #500 gb in kb
REDUCE_TO=1048576 #1 gb in kb

# and when it is larger, start deleting files accessed more than a certain 
# number of days ago until the cache is smaller than the configured size.

# Note the name of the variable _REDUCE_TO_: this should not be the total 
# amount of space  you can afford for the cache, but instead the total space 
# you can afford MINUS the amount you expect the cache to grow in between 
# executions of this script.

current_usage () {
	echo $(du -sk $CACHE_DIR | cut -f 1)
}

delete_total=0
max_age=60 # days
usage=$(current_usage)
start_size=$usage
run=1
while [ $usage -gt $REDUCE_TO ] && [ $max_age -ge -1 ]; do
	run=0
	echo $max_age
	echo $usage

	# files. loop (instead of -delete) so that we can keep count
	for f in $(find $CACHE_DIR -type f -atime +$max_age); do
		rm $f
		let delete_total+=1
	done

	# broken symlinks
	find -L $CACHE_DIR -type l -delete
	
	# empty directories
	find $CACHE_DIR -mindepth 1 -type d -empty -delete

	let max_age-=1
	usage=$(current_usage)
done

if [ $run == 0 ]; then
	echo -ne "$(date +[%c cache_clean.sh]) " >> $LOG
	echo -ne "Deleted $delete_count files to " >> $LOG
	echo "get cache from $start_size kb to $usage kb." >> $LOG
fi



