#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
webapp.py
=========
Implements IIIF 1.1 <http://www-sul.stanford.edu/iiif/image-api/1.1> level 2

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
from datetime import datetime
from decimal import Decimal, getcontext
from img_info import ImageInfo
from img_info import ImageInfoException
from img_info import InfoCache
from log_config import get_logger
from os import path, makedirs, unlink, removedirs, symlink
from parameters import RegionRequestException
from parameters import RegionSyntaxException
from parameters import RotationSyntaxException
from parameters import SizeRequestException
from parameters import SizeSyntaxException
from urllib import unquote, quote_plus
from werkzeug.http import parse_date, parse_accept_header, http_date
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response, BaseResponse, CommonResponseDescriptorsMixin
import constants
import img
import loris_exception
import random
import re
import resolver
import string
import transforms

try:
	import libuuid as uuid # faster. do pip install python-libuuid
except ImportError:
	import uuid

# Loris's etc dir MUST either be a sibling to the /loris/loris directory or at 
# the below:
ETC_DP = '/etc/loris'

# We can figure out everything else from there.

logger = get_logger(__name__)
getcontext().prec = 25 # Decimal precision. This should be plenty.

def create_app(debug=False):
	if debug:
		logger.debug('Running in debug mode.')
		project_dp = path.dirname(path.dirname(path.realpath(__file__)))

		# read the config
		conf_fp = path.join(project_dp, 'etc', 'loris.conf')
		config = __config_to_dict(conf_fp)

		# override some stuff to look at relative directories.
		config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
		config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
		config['loris.Loris']['enable_caching'] = True
		config['img.ImageCache']['cache_links'] = '/tmp/loris/cache/links'
		config['img.ImageCache']['cache_dp'] = '/tmp/loris/cache/img'
		config['img_info.InfoCache']['cache_dp'] = '/tmp/loris/cache/info'
		config['resolver.Resolver']['src_img_root'] = path.join(project_dp, 'tests', 'img')
	else:
		logger.debug('Running in production mode.')
		conf_fp = path.join(ETC_DP, 'loris.conf')
		config = __config_to_dict(conf_fp)

	# Make any dirs we may need 
	dirs_to_make = []
	try:
		dirs_to_make.append(config['loris.Loris']['tmp_dp'])
		if config['loris.Loris']['enable_caching']:
			dirs_to_make.append(config['img.ImageCache']['cache_dp'])
			dirs_to_make.append(config['img.ImageCache']['cache_links'])
			dirs_to_make.append(config['img_info.InfoCache']['cache_dp'])
		[makedirs(d) for d in dirs_to_make if not path.exists(d)]
	except OSError as ose: 
		from sys import exit
		from os import strerror
		# presumably it's permissions
		msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
		logger.fatal(msg)
		logger.fatal('Exiting')
		exit(77)
	else:
		return Loris(config, debug)

def __transform_sections_from_config(config):
	'''
	Args:
		config (dict)
	'''
	filt = lambda s: s.split('.')[0] == 'transforms'
	return filter(filt, config.keys())

def __config_to_dict(conf_fp):
	config_parser = RawConfigParser()
	config_parser.read(conf_fp)
	config = {}

	# shortcut, but everything comes in as a str
	[config.__setitem__(section, dict(config_parser.items(section)))
		for section in config_parser.sections()]

	# convert bools
	b = bool(int(config['loris.Loris']['enable_caching']))
	config['loris.Loris']['enable_caching'] = b

	b = bool(int(config['loris.Loris']['redirect_conneg']))
	config['loris.Loris']['redirect_conneg'] = b

	b = bool(int(config['loris.Loris']['redirect_base_uri']))
	config['loris.Loris']['redirect_base_uri'] = b

	b = bool(int(config['loris.Loris']['redirect_cannonical_image_request']))
	config['loris.Loris']['redirect_cannonical_image_request'] = b

	b = bool(int(config['loris.Loris']['enable_cors']))
	config['loris.Loris']['enable_cors'] = b

	# convert lists
	l = map(string.strip, config['loris.Loris']['cors_whitelist'].split(','))
	config['loris.Loris']['cors_whitelist'] = l

	# convert transforms.*.target_formats to lists
	for tf in __transform_sections_from_config(config):
		config[tf]['target_formats'] = [s.strip() for s in config[tf]['target_formats'].split(',')]

	return config

class LorisResponse(BaseResponse, CommonResponseDescriptorsMixin):
	'''Similar to Response, but IIIF Compliance Header is added and none of the
	ETagResponseMixin, ResponseStreamMixin, or WWWAuthenticateMixin capabilities
	See: http://werkzeug.pocoo.org/docs/wrappers/#werkzeug.wrappers.Response
	'''
	def __init__(self, response=None, status=None, content_type=None):
		super(LorisResponse, self).__init__(response=response, status=status, content_type=content_type)
		self.headers['Link'] = '<%s>;rel="profile"' % (constants.COMPLIANCE,)

class Loris(object):

	DEFAULT_IMAGE_FMT = 'DEFAULT'

	SIZE_REGEX = re.compile('^(full|\d+,|,\d+|!?\d+,\d+|pct:\d+)$')
	REGION_REGEX = re.compile('^(full|(pct:)?(\d+,){3}\d+)$')

	def __init__(self, app_configs={ }, debug=False):
		'''The WSGI Application.
		Args:
			config ({}): 
				A dictionary of dictionaries that represents the loris.conf 
				file.
			debug (bool)
		'''
		self.app_configs = app_configs
		logger.debug('Loris initialized with these settings:')
		[logger.debug('%s.%s=%s' % (key, sub_key, self.app_configs[key][sub_key]))
			for key in self.app_configs for sub_key in self.app_configs[key]]

		self.debug = debug

		# make the loris.Loris configs attrs for easier access
		_loris_config = self.app_configs['loris.Loris']
		self.tmp_dp = _loris_config['tmp_dp']
		self.www_dp = _loris_config['www_dp']
		self.enable_caching = _loris_config['enable_caching']
		self.redirect_conneg = _loris_config['redirect_conneg']
		self.redirect_base_uri = _loris_config['redirect_base_uri']
		self.redirect_cannonical_image_request = _loris_config['redirect_cannonical_image_request']
		self.default_format = _loris_config['default_format']
		self.enable_cors = _loris_config['enable_cors']
		self.cors_whitelist = _loris_config['cors_whitelist']

		deriv_formats = [tf.split('.')[1] 
			for tf in filter(lambda k: k.startswith('transforms.'), self.app_configs)]

		logger.debug(deriv_formats)

		self.transformers = {}
		for f in deriv_formats:
			self.transformers[f] = self._load_transformer('transforms.'+f)

		exts = ','.join(deriv_formats)
		rules = [
			Rule('/<path:ident>/<region>/<size>/<rotation>/<any(native,color,bitonal,grey):quality>.<any(png,jpg,gif):target_fmt>', endpoint='img'),
			Rule('/<path:ident>/<region>/<size>/<rotation>/<any(native,color,bitonal,grey):quality>.<bad_fmt>', endpoint='bad_img_format'),
			Rule('/<path:ident>/<region>/<size>/<rotation>/<any(native,color,bitonal,grey):quality>', endpoint='img'),
			Rule('/<path:ident>/info.json', endpoint='info'),
			Rule('/<path:ident>/info', endpoint='info_conneg'),
			Rule('/<path:wtf>', endpoint='info_redirect_or_error'),
			Rule('/favicon.ico', endpoint='favicon'),
			Rule('/', endpoint='index')
		]

		self.url_map = Map(rules)

		self.resolver = resolver.Resolver(self.app_configs['resolver.Resolver'])

		if self.enable_caching:
			self.info_cache = InfoCache(self.app_configs['img_info.InfoCache']['cache_dp'])
			cache_links = self.app_configs['img.ImageCache']['cache_links']
			cache_dp = self.app_configs['img.ImageCache']['cache_dp']
			self.img_cache = img.ImageCache(cache_dp,cache_links)

	def _load_transformer(self, name):
		clazz = self.app_configs[name]['impl']
		default_format = self.default_format
		transformer = getattr(transforms,clazz)(self.app_configs[name], default_format)
		logger.debug('Loaded Transformer %s' % self.app_configs[name]['impl'])
		return transformer

	def wsgi_app(self, environ, start_response):
		request = Request(environ)
		response = self.dispatch_request(request)
		return response(environ, start_response)

	def dispatch_request(self, request):
		'''
		Call the appropriate method based on the Rule that was matched. The Rule's
		endpoint attribute plus 'get_' will be the name of the method.
		'''
		adapter = self.url_map.bind_to_environ(request.environ)
		endpoint, values = adapter.match()
		return getattr(self, 'get_'+endpoint)(request, **values)

	def __call__(self, environ, start_response):
		'''
		This makes Loris executable.
		'''
		return self.wsgi_app(environ, start_response)

	def get_environment(self, request, ident):
		# For dev/debugging. Change any route to dispatch to 'environment'
		body = 'REQUEST ENVIRONMENT\n===================\n'
		for key in request.environ:
			body += '%s\n' % (key,)
			body += '\t%s\n' % (request.environ[key],)
		return BaseResponse(body, content_type='text/plain')

	def get_index(self, request):
		'''
		Just so there's something at /.
		'''
		f = file(path.join(self.www_dp, 'index.txt'))
		r = Response(f, content_type='text/plain')
		if self.enable_caching:
			r.add_etag()
			r.make_conditional(request)
		return r

	def get_favicon(self, request):
		f = path.join(self.www_dp, 'icons', 'loris-icon.png')
		r = Response(file(f), content_type='image/x-icon')
		if self.enable_caching:
			r.add_etag()
			r.make_conditional(request)
		return r

	def get_info_redirect_or_error(self, request, wtf):
		# This isn't foolproof, an identifier with 5 path-like segments could 
		# break it
		tokens = wtf.split('/')

		r = LorisResponse()

		if len(tokens) >= 5: # all the parts are there for an image request
			# check quality
			if tokens[-1].split('.')[0] not in ('native','color','grey','bitonal'):
				r.body = '(400) "%s" is not a valid quality' % (tokens[-1].split('.')[0],)
				r.status_code = 400
				r.mimetype = 'text/plain'
				return r
			# rotation, just make sure it's a digit here
			elif not tokens[-2].isdigit():
				body = '(400) rotation must be an integer between 0 and 360 ("%s" supplied)' % (tokens[-2],)
				r.status_code = 400
				r.mimetype = 'text/plain'
				return r
			# size
			elif not re.match(Loris.SIZE_REGEX, tokens[-3]):
				r.body = '(400) size syntax is not valid ("%s" supplied)' % (tokens[-3],)
				r.status_code = 400
				r.mimetype = 'text/plain'
				return r
			# region
			elif not re.match(Loris.REGION_REGEX, tokens[-4]):
				r.body = '(400) region syntax is not valid ("%s" supplied)' % (tokens[-4],)
				r.status_code = 400
				r.mimetype = 'text/plain'
				return r
			# ident
			elif not self.resolver.is_resolvable('%2F'.join(tokens[0:-4])):
				ident = '%2F'.join(tokens[0:-4])
				return Loris._not_resolveable_response(ident)
		else: #len(tokens) < 5:
			ident = '%2F'.join(tokens)
			if not self.resolver.is_resolvable(ident):
				return Loris._not_resolveable_response(ident)
			elif self.redirect_base_uri:
				to_location = Loris._info_dot_json_from_request(request)
				logger.debug('Redirected %s to %s' % (ident, to_location))
				r.headers['Location'] = to_location
				r.status_code = 303
				return r
			else:
				return self.get_info(request, ident)

	def get_bad_img_format(self, request, ident, region, size, rotation, quality, bad_fmt):
		body = '(415) format "%s" not supported or not valid' % (bad_fmt,)
		r = LorisResponse(response=body, status=415, content_type='text/plain')
		return r

	def get_info_conneg(self, request, ident):
		accept = request.headers.get('accept')
		if accept and not ('application/json' in accept or '*/*' in accept):
			return Loris._format_not_supported_response(accept)

		elif not self.resolver.is_resolvable(ident):
			return Loris._not_resolveable_response(ident)

		elif self.redirect_conneg:
			to_location = Loris._info_dot_json_from_request(request)
			logger.debug('Redirected %s to %s' % (ident, to_location))
			r = LorisResponse(status=301)
			r.headers['Location'] = to_location
			return r

		else:
			return self.get_info(request, ident)

	def get_info(self, request, ident):
		r = LorisResponse()
		if self.enable_cors and request.headers.get('origin'):
			if request.headers['origin'] in self.cors_whitelist:
				r.headers['access-control-allow-origin'] = request.headers['origin']

		try:
			info, last_mod = self._get_info(ident,request)
		except (ImageInfoException,resolver.ResolverException) as e:
			r.response = e
			r.status_code = e.http_status
			r.mimetype = 'text/plain'
		else:
			ims_hdr = request.headers.get('If-Modified-Since')

			ims = parse_date(ims_hdr)
			last_mod = parse_date(http_date(last_mod)) # see note under get_img

			if ims and ims >= last_mod:
				logger.debug('Sent 304 for %s ' % (ident,))
				r.status_code = 304
			else:
				if last_mod:
					r.last_modified = last_mod
				r.automatically_set_content_length
				# r.headers['Cache-control'] = 'public'
				callback = request.args.get('callback', None)
				if callback:
					r.mimetype = 'application/javascript'
					r.data = '%s(%s);' % (callback, info.to_json())
				else:
					r.content_type = 'application/json'
					r.data = info.to_json()
		finally:
			return r

	def _get_info(self,ident,request,src_fp=None,src_format=None):
		if self.enable_caching:
			in_cache = ident in self.info_cache
		else:
			in_cache = False

		if in_cache:
			return self.info_cache[ident]
		else:
			if not all((src_fp, src_format)):
				# get_img can pass in src_fp, src_format because it needs them
				# elsewhere; get_info does not.
				src_fp, src_format = self.resolver.resolve(ident)

			uri = Loris._base_uri_from_request(request)
			formats = self.transformers[src_format].target_formats
			
			logger.debug('Format: %s' % (src_format,))
			logger.debug('File Path: %s' % (src_fp,))
			logger.debug('Identifier: %s' % (ident,))

			# get the info
			info = ImageInfo.from_image_file(ident, uri, src_fp, src_format, formats)

			# store
			if self.enable_caching:
				self.info_cache[ident] = info
				# pick up the timestamp... :()
				info,last_mod = self.info_cache[ident]
			else:
				last_mod = None

			return (info,last_mod)

	
	def _format_from_request(self, r):
		filt = lambda v: v.startswith('image/')
		preferred_fmts = filter(filt, r.accept_mimetypes.values())
		if len(preferred_fmts) == 0:
			fmt = self.default_format
			logger.debug('No image type in accept header, using default: %s' % fmt)
		else:
			fmt = constants.FORMATS_BY_MEDIA_TYPE[preferred_fmts[0]]
			logger.debug('Format from conneg: %s' % fmt)
		return fmt

	def get_img(self, request, ident, region, size, rotation, quality, target_fmt=None):
		'''Get an Image. 
		Args:
			request (Request): 
				Forwarded by dispatch_request
			ident (str): 
				The identifier portion of the IIIF URI syntax

		'''
		r = LorisResponse()

		if target_fmt == None:
			target_fmt = self._format_from_request(request)
			logger.debug('target_fmt: %s' % (target_fmt,))

			if self.redirect_conneg:
				logger.debug(ident)
				image_request = img.ImageRequest(ident, region, size, rotation, quality, target_fmt)
				logger.debug('Attempting redirect to %s' % (image_request.request_path,))

				r.headers['Location'] = image_request.request_path
				r.status_code = 301
				return r
			# no reason for an else because the spec dictates that we should use a 
			# default format, which _format_from_request will return if one can't be
			# discerned from the Accept header.

		# ImageRequest's Parameter attributes, i.e. RegionParameter etc. are 
		# decorated with @property and not constructed until they are first 
		# accessed, which mean we don't have to catch any exceptions here.
		image_request = img.ImageRequest(ident, region, size, rotation, quality, target_fmt)

		logger.debug(image_request.request_path)

		if self.enable_caching:
			in_cache = image_request in self.img_cache
		else:
			in_cache = False

		if in_cache:
			fp = self.img_cache[image_request]

			ims_hdr = request.headers.get('If-Modified-Since')

			img_last_mod = datetime.utcfromtimestamp(path.getmtime(fp))
			# The stamp from the FS needs to be rounded using the same precision
			# as when went sent it, so for an accurate comparison turn it into
			# an http date and then parse it again :-( :
			img_last_mod = parse_date(http_date(img_last_mod))
			logger.debug("Time from FS (native, rounded): " + str(img_last_mod))
			logger.debug("Time from IMS Header (parsed): " + str(parse_date(ims_hdr)))
			# ims_hdr = parse_date(ims_hdr) # catch parsing errors?
			if ims_hdr and parse_date(ims_hdr) >= img_last_mod:
				logger.debug('Sent 304 for %s ' % (fp,))
				r.status_code = 304
				return r
			else:
				r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
				r.status_code = 200
				r.last_modified = img_last_mod
				r.headers['Content-Length'] = path.getsize(fp)
				r.response = file(fp)
				return r
		else:
			try:
				# 1. resolve the identifier
				src_fp, src_format = self.resolver.resolve(ident)

				# 2 hand the Image object its info
				info = self._get_info(ident, request, src_fp, src_format)[0]
				image_request.info = info

				# 3. Redirect if appropriate
				if self.redirect_cannonical_image_request:
					if not image_request.is_cannonical:
						logger.debug('Attempting redirect to %s' % (image_request.c14n_request_path,))
						r.headers['Location'] = image_request.c14n_request_path
						r.status_code = 301
						return r

				# 4. Make an image
				fp = self._make_image(image_request, src_fp, src_format)
				
			except (resolver.ResolverException, ImageInfoException, 
				img.ImageException,	RegionSyntaxException, 
				RegionRequestException, SizeSyntaxException,
				SizeRequestException, RotationSyntaxException) as e:
				r.response = e
				r.status_code = e.http_status
				r.mimetype = 'text/plain'
				return r

		r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
		r.status_code = 200
		r.last_modified = datetime.utcfromtimestamp(path.getctime(fp))
		r.headers['Content-Length'] = path.getsize(fp)
		r.response = file(fp)

		if not self.enable_caching:
			r.call_on_close(unlink(fp))

		return r

	def _make_image(self, image_request, src_fp, src_format):
		'''
		Args:
			image_request (img.ImageRequest)
			src_fp (str)
			src_format (str)
		Returns:
			(str) the fp of the new image
		'''
		# figure out paths, make dirs
		if self.enable_caching:
			p = path.join(self.img_cache.cache_root, Loris._get_uuid_path())
			target_dp = path.dirname(p)
			target_fp = '%s.%s' % (p, image_request.format)
			if not path.exists(target_dp):
				makedirs(target_dp)
		else:
			# random str
			n = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			target_fp = '%s.%s' % (path.join(self.tmp_dp, n), image_request.format)

		logger.debug('Target fp: %s' % (target_fp,))

		# Get the transformer
		transformer = self.transformers[src_format]

		transformer.transform(src_fp, target_fp, image_request)
		#  cache if caching (this makes symlinks for next time)
		if self.enable_caching:
			self.img_cache[image_request] = target_fp

		return target_fp

	@staticmethod
	def _get_uuid_path():
		# Make a pairtree-like path from a uuid
		# Wonder if this should be time.time() plus some random check chars,
		# just to make it shorter
		_id = uuid.uuid1().hex
		return path.sep.join([_id[i:i+2] for i in range(0, len(_id), 2)])

	@staticmethod
	def _base_uri_from_request(r):
		# See http://www-sul.stanford.edu/iiif/image-api/1.1/#url_encoding
		#
		# Consider a translation table (or whatever) instead of #quote_plus for 
		# 	"/" / "?" / "#" / "[" / "]" / "@" / "%"
		# if we run into trouble.

		# info
		if r.path.endswith('info') or r.path.endswith('info.json') :
			ident = '/'.join(r.path[1:].split('/')[:-1])
		# image
		elif r.path.split('/')[-1].split('.')[0] in ('native','color','grey','bitonal'):
			ident = '/'.join(r.path[1:].split('/')[:-4])
		# bare
		else:
			ident = r.path[1:] # no leading slash

		logger.debug(r.path)

		ident_encoded = quote_plus(ident)
		logger.debug('Re-encoded identifier: %s' % (ident_encoded,))

		if r.script_root != u'':
			uri = '%s%s' % (r.url_root,ident_encoded)
		else:
			uri = r.host_url + ident_encoded

		logger.debug('uri_from_request: %s' % (uri,))
		return uri

	@staticmethod
	def _info_dot_json_from_request(request):
		base_uri = Loris._base_uri_from_request(request)
		return '%s/info.json' % (base_uri,)

	@staticmethod
	def _not_resolveable_response(ident):
		ident = quote_plus(ident)
		msg = '404: Identifier "%s" does not resolve to an image.' % (ident,)
		r = LorisResponse(response=msg, content_type='text/plain', status=404)
		logger.warn(msg)
		return r

	@staticmethod
	def _format_not_supported_response(format):
		msg = '415: "%s" is not supported.' % (format,)
		r = LorisResponse(response=msg, content_type='text/plain', status=415)
		logger.warn(msg)
		
		logger.warn(msg)
		return r

if __name__ == '__main__':
	from werkzeug.serving import run_simple
	extra_files = []

	project_dp = path.dirname(path.dirname(path.realpath(__file__)))
	conf_fp = path.join(project_dp, 'etc', 'loris.conf')
	extra_files.append(conf_fp)

	app = create_app(debug=True)

	run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True,
		extra_files=extra_files)
