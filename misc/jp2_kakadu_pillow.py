# This the basic flow for getting from a JP2 to a jpg w/ kdu_expand and Pillow
# Useful for debugging the scenario independent of the server.

from PIL import Image
from PIL.ImageFile import Parser
from os import makedirs, path, unlink
import subprocess
import sys

KDU_EXPAND='/usr/local/bin/kdu_expand'
LIB_KDU='/usr/local/lib/libkdu_v72R.so'
TMP='/tmp'
INPUT_JP2='/home/jstroop/workspace/loris/tests/img/corrupt.jp2'
OUT_JPG='/tmp/test.jpg'
REDUCE=0

### cmds, etc.
pipe_fp = '%s/mypipe.bmp' % (TMP,)
kdu_cmd = '%s -i %s -o %s -num_threads 4 -reduce %d' % (KDU_EXPAND, INPUT_JP2, pipe_fp, REDUCE)
mkfifo_cmd = '/usr/bin/mkfifo %s' % (pipe_fp,)
rmfifo_cmd = '/bin/rm %s' % (pipe_fp,)

# make a named pipe
mkfifo_resp = subprocess.check_call(mkfifo_cmd, shell=True)
if mkfifo_resp == 0:
    print 'mkfifo OK'

# write kdu_expand's output to the named pipe 
kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, 
    bufsize=-1, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
    env={ 'LD_LIBRARY_PATH' : KDU_EXPAND })

# open the named pipe and parse the stream
with open(pipe_fp, 'rb') as f:
    p = Parser()
    while True:
        s = f.read(1024)
        if not s:
            break
        p.feed(s)
    im = p.close()

# finish kdu
kdu_exit = kdu_expand_proc.wait()
if kdu_exit != 0:
    map(sys.stderr.write, kdu_expand_proc.stderr)
else:
    # if kdu was successful, save to a jpg
    map(sys.stdout.write, kdu_expand_proc.stdout)
    im = im.resize((719,900), resample=Image.ANTIALIAS)
    im.save(OUT_JPG, quality=95)

# remove the named pipe
rmfifo_resp = subprocess.check_call(rmfifo_cmd, shell=True)
if rmfifo_resp == 0:
    print 'rm fifo OK'
