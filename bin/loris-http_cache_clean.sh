#!/bin/bash

#
# cache_clean.sh
# Cron script for maintaining the loris cache size.
#
# CAUTION - This script deletes files. Be careful where you point it!
#
LOG="/var/log/loris/cache_clean.log"

# Check that the cache directories...
IMG_CACHE_ROOT_DIR="/usr/local/share/images/loris"
IMG_CACHE_DP_DIR="/var/cache/loris/img"
IMG_CACHE_LINKS_DIR="/var/cache/loris/links"

# ...is below a certain size...
# REDUCE_TO=1048576 #1 gb
# REDUCE_TO=1073741824 # 1 TB
# REDUCE_TO=2147483648 # 2 TB
REDUCE_TO=20971520 #20 gb

# ...and when it is larger, start deleting files accessed more than a certain 
# number of days ago until the cache is smaller than the configured size.

# Note the name of the variable __REDUCE_TO__: this should not be the total 
# amount of space you can afford for the cache, but instead the total space 
# you can afford MINUS the amount you expect the cache to grow in between 
# executions of this script.

current_usage_cache_root () {
	du -sk IMG_CACHE_ROOT_DIR | cut -f 1
}

current_usage_cache_dp () {
	du -sk IMG_CACHE_DP_DIR | cut -f 1
}

delete_total=0
max_age=60 # days
usage=$(current_usage_cache_dp)+$(current_usage_cache_root)
start_size=$usage
run=1
while [ $usage -gt $REDUCE_TO ] && [ $max_age -ge -1 ]; do
	run=0

	# files. loop (instead of -delete) so that we can keep count
	for f in $(find $IMG_CACHE_ROOT_DIR -name loris_cache.* -type f -atime +$max_age); do
		rm $f
		let delete_total+=1
	done

	# files. loop (instead of -delete) so that we can keep count
	for f in $(find $IMG_CACHE_DP_DIR -type f -atime +$max_age); do
		rm $f
		let delete_total+=1
	done

    # empty directories
	find $IMG_CACHE_ROOT_DIR -mindepth 1 -type d -empty -delete
	find $IMG_CACHE_DP_DIR -mindepth 1 -type d -empty -delete

	# broken symlinks
	find -L $IMG_CACHE_LINKS_DIR -type l -delete
	find $IMG_CACHE_LINKS_DIR -mindepth 1 -type d -empty -delete

	let max_age-=1
	usage=$(current_usage_cache_dp)+$(current_usage_cache_root)
done

echo -ne "$(date +[%c]) " >> $LOG
if [ $run == 0 ]; then
	echo -ne "Deleted $delete_count files to " >> $LOG
	echo "get cache from $start_size kb to $usage kb." >> $LOG
else
	echo "Cache at $usage kb (no deletes required)." >> $LOG
fi




