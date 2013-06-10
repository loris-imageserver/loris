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
from parameters import RegionRequestException
from parameters import RegionSyntaxException
from parameters import RotationSyntaxException
from parameters import SizeRequestException
from parameters import SizeSyntaxException
from urllib import unquote, quote_plus
from werkzeug import http
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response
import constants
import img
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

		# read the config
		conf_fp = path.join(project_dp, 'etc', 'loris.conf')
		config = __config_to_dict(conf_fp)

		# override some stuff to look at relative directories.
		config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
		config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
		config['loris.Loris']['cache_dp'] = '/tmp/loris/cache'
		config['loris.Loris']['enable_caching'] = True
		config['resolver.Resolver']['src_img_root'] = path.join(project_dp, 'tests', 'img')
	else:
		logger.info('Running in production mode.')
		conf_fp = path.join(ETC_DP, 'loris.conf')
		config = __config_to_dict(conf_fp)

	# Make any dirs we may need 

	dirs_to_make = []
	try:
		dirs_to_make.append(config['loris.Loris']['tmp_dp'])
		if config['loris.Loris']['enable_caching']:
			dirs_to_make.append(config['loris.Loris']['cache_dp'])
		[makedirs(d) for d in dirs_to_make if not path.exists(d)]
	except OSError as ose: 
		from sys import exit
		from os import strerror
		msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
		logger.fatal(msg)
		logger.fatal('Exiting')
		exit(77)
	else:
		return Loris(config, debug)

def __config_to_dict(conf_fp):
	config_parser = RawConfigParser()
	config_parser.read(conf_fp)
	config = {}
	[config.__setitem__(section, dict(config_parser.items(section)))
		for section in config_parser.sections()]
	# Do any type conversions
	config['loris.Loris']['enable_caching'] = bool(int(config['loris.Loris']['enable_caching']))
	config['loris.Loris']['redirect_conneg'] = bool(int(config['loris.Loris']['redirect_conneg']))
	config['loris.Loris']['redirect_base_uri'] = bool(int(config['loris.Loris']['redirect_base_uri']))
	config['loris.Loris']['redirect_cannonical_image_request'] = bool(int(config['loris.Loris']['redirect_cannonical_image_request']))
	return config

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
			Rule('/<path:ident>/info', endpoint='info_conneg'),
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
		body = 'REQUEST ENVIRONMENT\n===================\n'
		for key in request.environ:
			body += '%s\n' % (key,)
			body += '\t%s\n' % (request.environ[key],)
		return Response(body, content_type='text/plain')

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

	def get_info_redirect(self, request, ident):
		if not self.resolver.is_resolvable(ident):
			return Loris.__not_resolveable_response(ident)

		elif self.config['loris.Loris']['redirect_base_uri']:
			to_location = Loris.__info_json_from_unsecaped_ident(ident)
			logger.debug('Redirected %s to %s' % (ident, to_location))
			return redirect(to_location, code=303)
		else:
			return self.get_info(request, ident)

	def get_info_conneg(self, request, ident):
		accept = request.headers.get('accept')
		if accept and accept not in ('application/json', '*/*'):
			return Loris.__format_not_supported_response(accept)

		elif not self.resolver.is_resolvable(ident):
			return Loris.__not_resolveable_response(ident)

		elif self.config['loris.Loris']['redirect_conneg']:
			to_location = Loris.__info_json_from_unsecaped_ident(ident)
			logger.debug('Redirected %s to %s' % (ident, to_location))
			return redirect(to_location, code=301)

		else:
			return self.get_info(request, ident)

	def get_info(self, request, ident):
		
		# TODO: needs a compliance link header

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
			uri = Loris.__base_uri_from_request(request)

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
			r.make_conditional(request)
		return r


	def get_img(self, request, ident, region, size, rotation, quality):
		'''Get an Image. 
		Args:
			request (Request): 
				Forwarded by dispatch_request
			ident (str): 
				The identifier portion of the IIIF URI syntax

		'''

		if '.' in quality:
			quality,target_fmt = quality.split('.')
		else:
			# TODO:, will need to use conneg and possibly redirect
			# Either way detemine target_fmt from Accept header.
			target_fmt = 'xxx'

		# start an image object
		image = img.Image(ident, region, size, rotation, quality, target_fmt)

		headers = Headers()
		headers['Link'] = RelatedLinksHeader()
		headers['Link']['profile'] = constants.COMPLIANCE
		r = Response(headers=headers)

		in_cache = False # TODO: replace with blah 'image in cache'
		# do a quick cache check:
		if self.config['loris.Loris']['enable_caching'] and in_cache:
			pass
			# see http://werkzeug.pocoo.org/docs/wrappers/
			# make conditional and __return__ if the file exists.
		else:
			base_uri = Loris.__base_uri_from_request(request)
			try:
				# 1. resolve the identifier
				fp, src_fmt = self.resolver.resolve(ident)
				# 2 hand the Image object its info.
				info = self.__get_info(ident, base_uri, fp, src_fmt)
				image.info = info

				# 3. Redirect if appropriate, else set the cannonical 
				# Link header (non-normative):

				# TODO: need tests for:
				# link header if redirecting is not enabled
				# redirecting if it is enabled

				if self.config['loris.Loris']['redirect_cannonical_image_request']:
					if not image.is_cannonical:
						logger.debug('Attempting redirect to %s' % (image.c14n_request_path,))
						return redirect(image.c14n_request_path, code=301)
				else:
					if not image.is_cannonical:
						cannonical_uri = '%s/%s' % (base_uri, image.c14n_request_path)
						logger.debug('cannonical_uri: %s' % (cannonical_uri,))
						headers['Link']['cannonical'] = cannonical_uri
				#
				# 4. If caching, use the above to build the cannonical path for 
				# the cache (all pixel pased)
				#
				# 5. Make an image, 
				#	a. if caching, save it to cache, else to tmp
				#	b  if caching, make a symlink from the original request path 
				#		(with pcts) to the cannonical path
				# 	c. return the image as a file object
				# 	d. if not caching, clean up
				
			except (resolver.ResolverException, img_info.ImageInfoException, 
				img.ImageException,	RegionSyntaxException, 
				RegionRequestException, SizeSyntaxException,
				SizeRequestException, RotationSyntaxException) as e:
				r.response = e
				r.status_code = e.http_status
				r.mimetype = 'text/plain'
				return r

		return r

	def __get_image(self, image):
		'''Check the cache first, otherwise make a new image.

		Args:
			image (str): The image's identifier.
			fp (str): The image's file path on the local file system.
		Raises:
			img_info.ImageInfoException when anything goes wrong.
		Returns:
			ImageInfo
		'''
		if self.config['loris.Loris']['enable_caching']:
			pass
		else:
			pass


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
	def __base_uri_from_request(r):
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
	def __info_json_from_unsecaped_ident(ident):
		ident = quote_plus(ident)
		# leading / or not?
		return '/%s/info.json' % (ident,)

	@staticmethod
	def __not_resolveable_response(ident):
		ident = quote_plus(ident)
		msg = '404: Identifier "%s" does not resolve to an image.' % (ident,)
		logger.warn(msg)
		return Response(msg, status=404, content_type='text/plain')

	@staticmethod
	def __format_not_supported_response(format):
		msg = '415: "%s" is not supported.' % (format,)
		logger.warn(msg)
		return Response(msg, status=415, content_type='text/plain')



class RelatedLinksHeader(dict):
	'''Not a full impl. of rfc 5988 (though that would be fun!); just enough 
	for our purposes. Use the rel as the key and the URI as the value.
	'''
	def __init__(self):
		super(RelatedLinksHeader, self).__init__()

	def __str__(self):
		return ','.join(['<%s>;rel="%s"' % (i[1],i[0]) for i in self.items()])





if __name__ == '__main__':
	from werkzeug.serving import run_simple
	extra_files = []

	project_dp = path.dirname(path.dirname(path.realpath(__file__)))
	conf_fp = path.join(project_dp, 'etc', 'loris.conf')
	extra_files.append(conf_fp)

	app = create_app(debug=True)

	run_simple('localhost', 5000, app, use_debugger=True, use_reloader=True,
		extra_files=extra_files)
