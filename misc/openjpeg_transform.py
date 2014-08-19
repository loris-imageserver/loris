
# Here's why we can't use PIL's API for OpenJPEG
# See http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html#jpeg-2000
import timeit
import subprocess
from PIL import Image
from PIL.ImageFile import Parser
import subprocess
import sys

def mk_tile_with_PIL():
	jp2_with_tiles_fp = '../tests/img/01/02/0001.jp2'
	im = Image.open(jp2_with_tiles_fp)
	im.reduce = 2
	im = im.crop((0,0,256,256))
	im.save('/tmp/out.jpg')

setup = 'from __main__ import mk_tile_with_PIL'
t = timeit.timeit('mk_tile_with_PIL()', setup=setup, number=3)
print 'Average with PIL: %0.6f' % (t,)


def mk_tile_subproc():
	opj_bin = '/usr/local/bin/opj_decompress'
	opj_lib = '/usr/local/lib/libopenjp2.so'
	pipe_o = '/tmp/mypipe.bmp'
	out_jpg = '/tmp/test.jpg'
	mkfifo_cmd = '/usr/bin/mkfifo %s' % (pipe_o,)
	rmfifo_cmd = '/bin/rm %s' % (pipe_o,)
	i = '../tests/img/01/02/0001.jp2'
	r = 2 # reduce
	# d = '256,256,512,512'
	d = '0,0,256,256'

	opj_cmd = '%s -i %s -o %s -d %s -r %s' % (opj_bin, i, pipe_o, d, r)

	# make a named pipe
	mkfifo_resp = subprocess.check_call(mkfifo_cmd, shell=True)
	if mkfifo_resp != 0:
	    sys.stderr.write('mkfifo not OK\n')

	# write opj_decompress's output to the named pipe 
	opj_proc = subprocess.Popen(opj_cmd, shell=True, 
	    bufsize=-1, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
	    env={ 'LD_LIBRARY_PATH' : opj_lib })

	# open the named pipe and parse the stream
	im = None
	with open(pipe_o, 'rb') as f:
	    p = Parser()
	    while True:
	        s = f.read(1024)
	        if not s:
	            break
	        p.feed(s)
	    im = p.close()

	# finish opj
	opj_exit = opj_proc.wait()
	if opj_exit != 0:
	    map(sys.stderr.write, opj_proc.stderr)
	else:
	    # opj was successful, save to a jpg
	    # map(sys.stdout.write, opj_proc.stdout)
	    im.save(out_jpg, quality=95)

	# remove the named pipe
	rmfifo_resp = subprocess.check_call(rmfifo_cmd, shell=True)
	if rmfifo_resp != 0:
	    sys.stderr.write('rm fifo not OK\n')

setup = 'from __main__ import mk_tile_subproc'
t = timeit.timeit('mk_tile_subproc()', setup=setup, number=3)
print 'Average with shellout to subprocess: %0.6f' % (t,)
