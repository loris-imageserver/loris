#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
webapp.py
==========
'''
from ConfigParser import RawConfigParser
from decimal import Decimal, getcontext
from log_config import get_logger
from os import path, makedirs
from urllib import unquote
from werkzeug import http
from werkzeug.datastructures import Headers, ResponseCacheControl
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
import constants
import img_info
import loris_exception
import resolver

# Loris's etc MUST either be a sibling to the loris directory or at /etc/loris
ETC_DP = '/etc/loris'
# everything else we can figure out from there.

logger = get_logger(__name__)
getcontext().prec = 25 # Decimal precision. This should be plenty.

def create_app(debug=False):
	if debug:
		logger.info('Running in debug mode.')
		project_dp = path.dirname(path.dirname(path.realpath(__file__)))
		config = {}
		config['loris.Loris'] = {}
		config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
		config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
		config['loris.Loris']['cache_dp'] = '/tmp/loris/cache'
		config['loris.Loris']['enable_caching'] = True
		# config['loris.Loris']['enable_caching'] = False
		config['resolver.Resolver'] = {}
		config['resolver.Resolver']['src_img_root'] = path.join(project_dp, 'test', 'img')
	else:
		logger.info('Running in production mode.')
		conf_fp = path.join(ETC_DP, 'loris.conf')
		config_parser = RawConfigParser()
		config_parser.read(conf_fp)
		config = {}
		[config.__setitem__(section, dict(config_parser.items(section)))
			for section in config_parser.sections()]
		config['loris.Loris']['enable_caching'] = bool(int(config['loris.Loris']['enable_caching']))

	# make 
	dirs_to_make = [ ]
	dirs_to_make.append(config['loris.Loris']['tmp_dp'])

	if config['loris.Loris']['enable_caching']:
		dirs_to_make.append(config['loris.Loris']['cache_dp'])
	
	[makedirs(d) for d in dirs_to_make if not path.exists(d)]

	return Loris(config)

class Loris(object):
	def __init__(self, config={}):
		'''The webapp. Mostly routing and, within public methods branching based 
		caching and cache behaviour is handled here.

		Args:
			Config {}: 
				A dictionary of dictionaries that represents the loris.conf 
				file.
		'''
		self.config = config
		logger.info('Loris initialized with these settings:')
		[logger.info('%s.%s=%s' % (key, sub_key, config[key][sub_key]))
			for key in config for sub_key in config[key]]

		self.url_map = Map([
			Rule('/<path:ident>/<region>/<size>/<rotation>/<quality>', endpoint='img'),
			Rule('/<path:ident>/info.json', endpoint='info'),
			Rule('/<path:ident>/info', endpoint='info'),
			# Rule('/<path:ident>', endpoint='info'), redirect to info
			Rule('/favicon.ico', endpoint='favicon'),
			Rule('/', endpoint='index'),
		])

		self.resolver = resolver.Resolver(self.config['resolver.Resolver'])

		if self.config['loris.Loris']['enable_caching']:
			self.info_cache = img_info.InfoCache()

	def wsgi_app(self, environ, start_response):
		request = Request(environ)
		response = self.dispatch_request(request)
		return response(environ, start_response)

	def dispatch_request(self, request):
		adapter = self.url_map.bind_to_environ(request.environ)
		endpoint, values = adapter.match()
		return getattr(self, 'get_'+endpoint)(request, **values)

	def __call__(self, environ, start_response):
		return self.wsgi_app(environ, start_response)

	def get_index(self, request):
		www_dp = self.config['loris.Loris']['www_dp']
		f = file(path.join(www_dp, 'index.txt'))
		r = Response(f, mimetype='text/plain')
		if self.config['loris.Loris']['enable_caching']:
			r.add_etag()
			r.make_conditional(request)
		return r

	def get_favicon(self, request):
		www_dp = self.config['loris.Loris']['www_dp']
		f = path.join(www_dp, 'icons', 'loris-icon.png')
		r = Response(file(f), content_type='image/x-icon')
		if self.config['loris.Loris']['enable_caching']:
			r.add_etag()
			r.make_conditional(request)
		return r

	def get_info(self, request, ident):
		# this will never work if caching is disabled because it will never be
		# stored by __get_img_info. This just allows us to quickly sidestep
		# resolving the identifier etc if we have the info in memory.
		r = Response()
		info = None

		# Do a quick check of the memory cache
		if self.config['loris.Loris']['enable_caching']:
			info = self.info_cache.get(ident)

		if info is None:
			# 1. resolve the identifier
			try:
				fp, fmt = self.resolver.resolve(ident)
			except resolver.ResolverException as re:
				r.response = re
				r.status_code = re.http_status
				r.mimetype = 'text/plain'
				return r

			logger.debug('Format: %s' % (fmt,))
			logger.debug('File Path: %s' % (fp,))
			logger.debug('Identifier: %s' % (ident,))
			# 2. get the image's info
			try:
				info = self.__get_info(ident, fp, fmt)
			except img_info.ImageInfoException as iie:
				r.response = iie
				r.status_code = iie.http_status
				r.mimetype = 'text/plain'
				return r
		else:
			logger.debug('Got info for %s from info cache' % (ident,))

		r.mimetype = 'application/json' # TODO: right?
		r.data = info.to_json()
		if self.config['loris.Loris']['enable_caching']:
			r.add_etag()
			r.make_conditional(request)
		return r

	def get_img(self, request, ident, region, size, rotation, quality):
		'''Get an Image. 
		Args:
			request (Request): 
				Forwarded by dispatch_request
			ident (str): 
				The identifier portion of the IIIF URI syntax
			# iiif_params (RegionParameter, SizeParameter, RotationParameter, str, str):
			# 	A 5 tuple (region, size, rotation, quality, format)

		'''
		if '.' in quality:
			quality,format_ext = quality.split('.')
		else:
			fmt = None
			# TODO, will need to use conneg

		ident, region, size = map(unquote, (ident, region, size))

		logger.debug('region slice: %s' % (str(region),))
		logger.debug('size slice: %s' % (str(size),))
		logger.debug('rotation slice: %s' % (str(rotation),))
		logger.debug('quality slice: %s' % (quality))
		logger.debug('format extension: %s' % (format_ext))

		r = Response()
		cache_path = self.__img_elements_to_cache_path(ident, region, size, rotation, quality, format_ext)

		# try the cache
		if self.config['loris.Loris']['enable_caching'] and path.exists(cache_path[0]):
			# TODO: untested until we actually have stuff cached
			logger.debug('%s read from cache' % (cache_path[0],))
			r.data = cache_path[0]
			r.content_type = constants.FORMATS_BY_EXTENSION[cache_path[0].split('.')[-1]]
			r.add_etag()
			r.make_conditional(request)

		else:
			# 1. resolve the identifier
			try:
				fp, fmt = self.resolver.resolve(ident)
			except resolver.ResolverException as re:
				r.response = re
				r.status_code = re.http_status
				r.mimetype = 'text/plain'
				return r

			# 2. get the image's info
			try:
				info = self.__get_img_info(ident, fp, fmt)
			except img_info.ImageInfoException as iie:
				r.response = iie
				r.status_code = iie.http_status
				r.mimetype = 'text/plain'
				return r				
			# 3. instantiate these:
			# region_param = RegionParameter(region)
			# size_param = SizeParameter(size)
			# rotation_param = RotationParameter(rotation)
			# 
			# 4. If caching, use the above to build the cannonical path for the 
			# 		cache (all pixel pased)
			# 5. Make an image, 
			#	a. if caching, save it to cache, else to tmp
			#	b  if caching, make a symlink from the original request path 
			#		(with pcts) to the pixel-based path
			# 	c. return the image as a file object
			# 	d. if not caching, clean up

		return r

	def __img_elements_to_cache_path(self, ident, region, size, rotation, quality, format_ext):
		'''Return a two-tuple, The path to the file[0], and the path to the 
		file's directory[1].
		'''
		cache_dp = self.config['loris.Loris']['cache_dp']
		img_fp = '%s.%s' % (path.join(cache_dp, region, size, rotation, quality), format_ext)
		img_dp = path.dirname(img_fp)
		return (img_fp, img_dp)

	def __get_info(self, ident, fp, src_format):
		'''Check the memory cache, then the file system, and then, as a last 
		resort, construct a new ImageInfo object.

		Args:
			ident (str): The image's identifier.
			fp (str): The image's file path on the local file system.
		Raises:
			img_info.ImageInfoException when anything goes wrong.
		Returns:
			ImageInfo
		'''
		info = None
		if self.config['loris.Loris']['enable_caching']:
			# check memory
			if ident in self.info_cache:
				logger.debug('Info found in memory cache for %s' % (ident,))
				info = self.info_cache.get(ident)
			else:
				cache_root = self.config['loris.Loris']['cache_dp']
				cache_dir = path.join(cache_root, ident)
				cache_path = path.join(cache_dir, 'info.json')
				# Check the filesystem
				if path.exists(cache_path):
					logger.debug('Info for %s taken from filesystem' % (ident,))
					info = img_info.ImageInfo.from_json(cache_path)
				# Else get it
				else:
					logger.debug('Need to get info for %s from image...' % (ident,))
					info = img_info.ImageInfo.from_image_file(ident, fp, src_format)
					# save to the filesystem
					if not path.exists(cache_dir): 
						makedirs(cache_dir, 0755)
					f = open(cache_path, 'w')
					f.write(info.to_json())
					f.close()
					logger.info('Created: %s' % (cache_path,))

				# Don't forget to keep in memory!
				self.info_cache[ident] = info
		else:
			logger.debug('Info for %s taken from filesystem' % (ident,))	
			info = img_info.ImageInfo.from_image_file(ident, fp, src_format)

		return info

if __name__ == '__main__':
	from werkzeug.serving import run_simple
	extra_files = []

	app = create_app(debug=True)

	run_simple('localhost', 5000, app, use_debugger=True, use_reloader=True,
		extra_files=extra_files)
