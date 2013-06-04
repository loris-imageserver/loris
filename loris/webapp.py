#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
webapp.py
=========
Implements IIIF 1.1 <http://www-sul.stanford.edu/iiif/image-api> level 1 and 
most of level 2 (all but return of JPEG 2000 derivatives).

	Copyright (C) 2013 Jon Stroop

	This program is free software: you can redistribute it and/or modify it 
	under the terms of the GNU General Public License as published by the Free 
	Software Foundation, either version 3 of the License, or (at your option) 
	any later version.

	This program is distributed in the hope that it will be useful, but WITHOUT 
	ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
	FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for 
	more details.

	You should have received a copy of the GNU General Public License along 
	with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from ConfigParser import RawConfigParser
from decimal import Decimal, getcontext
from log_config import get_logger
from os import path, makedirs
from parameters import BadRegionRequestException
from parameters import BadRegionSyntaxException
from parameters import RegionParameter
from urllib import unquote, quote_plus
from werkzeug import http
from werkzeug.datastructures import ResponseCacheControl
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response
import constants
import img_info
import loris_exception
import resolver

# Loris's etc dir MUST either be a sibling to the /loris/loris directory or at 
# the below:
ETC_DP = '/etc/loris'
# We can figure out everything else from there.

logger = get_logger(__name__)
getcontext().prec = 25 # Decimal precision. This should be plenty.

def create_app(debug=False):
	if debug:
		logger.info('Running in debug mode.')
		project_dp = path.dirname(path.dirname(path.realpath(__file__)))
		config = { }
		config['loris.Loris'] = {}
		config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
		config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
		config['loris.Loris']['cache_dp'] = '/tmp/loris/cache'
		config['loris.Loris']['enable_caching'] = True
		# config['loris.Loris']['enable_caching'] = False
		config['resolver.Resolver'] = {}
		config['resolver.Resolver']['src_img_root'] = path.join(project_dp, 'tests', 'img')
	else:
		logger.info('Running in production mode.')
		conf_fp = path.join(ETC_DP, 'loris.conf')
		config_parser = RawConfigParser()
		config_parser.read(conf_fp)
		config = {}
		[config.__setitem__(section, dict(config_parser.items(section)))
			for section in config_parser.sections()]
		config['loris.Loris']['enable_caching'] = bool(int(config['loris.Loris']['enable_caching']))

	dirs_to_make = []
	dirs_to_make.append(config['loris.Loris']['tmp_dp'])

	if config['loris.Loris']['enable_caching']:
		dirs_to_make.append(config['loris.Loris']['cache_dp'])
	
	[makedirs(d) for d in dirs_to_make if not path.exists(d)]

	return Loris(config, debug)

class Loris(object):
	def __init__(self, config={}, debug=False):
		'''The webapp. Mostly routing and, within public methods branching based 
		caching and cache behaviour is handled here.

		Args:
			config ({}): 
				A dictionary of dictionaries that represents the loris.conf 
				file.
			debug (bool):
				True make is possible to dump the wsgi environment to the
				browser.
		'''
		self.debug = debug
		self.config = config
		logger.info('Loris initialized with these settings:')
		[logger.info('%s.%s=%s' % (key, sub_key, config[key][sub_key]))
			for key in config for sub_key in config[key]]

		rules = [
			Rule('/<path:ident>/<region>/<size>/<rotation>/<quality>', endpoint='img'),
			Rule('/<path:ident>/info.json', endpoint='info'),
			Rule('/<path:ident>/info', endpoint='info'),
			Rule('/<path:ident>', endpoint='info_redirect'),
			Rule('/favicon.ico', endpoint='favicon'),
			Rule('/', endpoint='index')
		]

		self.url_map = Map(rules)

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

	def get_environment(self, request, ident):
		# For dev/debugging. Change any route to dispatch to 'environment'
		body = 'REQUEST ENVIRONMENT\n'
		body += '===================\n'
		for key in request.environ:
			body += '%s\n' % (key,)
			body += '\t%s\n' % (request.environ[key],)
		return Response(body, content_type='text/plain')

	def get_info_redirect(self, request, ident):
		if self.resolver.is_resolvable(ident):
			ident = quote_plus(ident)
			to_location = '/%s/info.json' % (ident,) # leading / or not?
			logger.debug('Redirected %s to %s' % (ident, to_location))
			return redirect(to_location, code=303)
		else:
			# TODO: does this match other bad requests as well? If so, try to 
			# tweak routing or else change the message.
			return Loris.__not_resolveable_response(ident)

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

			# get the uri (@id)
			uri = Loris.__uri_from_request(request)

			# 2. get the image's info
			try:
				info = self.__get_info(ident, uri, fp, fmt)
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
			# TODO: make sure a Date is included.
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
				uri = Loris.__uri_from_request(request)
				info = self.__get_info(ident, uri, fp, fmt)
			except img_info.ImageInfoException as iie:
				r.response = iie
				r.status_code = iie.http_status
				r.mimetype = 'text/plain'
				return r

			# 3. instantiate these:
			try:
				region_param = RegionParameter(region, info)
			except (BadRegionSyntaxException,BadRegionRequestException) as bre:
				r.response = bre
				r.status_code = bre.http_status
				r.mimetype = 'text/plain'
				return r

			# size_param = SizeParameter(size)
			# rotation_param = RotationParameter(rotation)

			# 4. From each param object, use .cannonical_uri_value to build the 
			# the cannonical URI. Make redirecting an option. Otherwise add 
			# rel="cannonical" Link header
			# 
			# 5. If caching, use the above to build the cannonical path for the 
			# 		cache (all pixel pased)
			# 6. Make an image, 
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

	def __get_info(self, ident, uri, fp, src_format):
		'''Check the memory cache, then the file system, and then, as a last 
		resort, construct a new ImageInfo object from the image.

		Args:
			uri (str): The image's identifier.
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
					info = img_info.ImageInfo.from_image_file(ident, uri, fp, src_format)
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
			logger.debug('Info for %s taken from filesystem' % (uri,))	
			info = img_info.ImageInfo.from_image_file(ident, uri, fp, src_format)

		return info

	@staticmethod
	def __uri_from_request(r):
		# See http://www-sul.stanford.edu/iiif/image-api/1.1/#url_encoding
		#
		# TODO: This works on the embedded dev server but may need revisiting 
		# once on a production server.
		#
		# Consider a translation table (or whatever) instead of #quote_plus for 
		# 	"/" / "?" / "#" / "[" / "]" / "@" / "%"
		# if we run into trouble.
		from_end = -1 if r.path.endswith('info') or r.path.endswith('info.json') else -4
		ident = '/'.join(r.path[1:].split('/')[:from_end])
		ident_encoded = quote_plus(ident)
		logger.debug('Re-encoded identifier: %s' % (ident_encoded,))

		if r.script_root != u'':
			uri = r.host_url + '/'.join((r.script_root, ident_encoded))
		else:
			uri = r.host_url + ident_encoded

		logger.debug('uri_from_request: %s' % (uri,))
		return uri

	@staticmethod
	def __not_resolveable_response(ident):
		ident = quote_plus(ident)
		msg = '404: Identifier "%s" does not resolve to an image.' % (ident,)
		return Response(msg, status=404, content_type='text/plain')

if __name__ == '__main__':
	from werkzeug.serving import run_simple
	extra_files = []

	app = create_app(debug=True)

	run_simple('localhost', 5000, app, use_debugger=True, use_reloader=True,
		extra_files=extra_files)
