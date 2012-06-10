#!/usr/bin/env python

from patokah import create_app, BadRegionPctException, BadRegionSyntaxException
from werkzeug.test import Client
from werkzeug.testapp import test_app
from werkzeug.wrappers import BaseResponse
import ast
import os
import unittest

class TestPatokah(unittest.TestCase):
	
	def setUp(self):
		unittest.TestCase.setUp(self)
		self.app = create_app()
	
	def test_converters(self):
		# queries are based on the examples in the region, rotation and size sections
		pass_queries = {
			'simple' :{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/full/full/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'level':None, 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':0
			},
			'region_pixels':{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/80,50,16,75/full/0/native.jpg',
				'region' :{'is_pct':False, 'is_full':False, 'x':80, 'y':50, 'w':16, 'h':75},
				'size':{'force_aspect':None, 'level':None, 'pct':None, 'is_full':True, 'w':None, 'h':None},
				'rotation':0
			},
			'region_pct':{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/pct:10,10,70,80/full/0/native.jpg',
				'region' :{'is_pct':True, 'is_full':False, 'x':10, 'y':10, 'w':70, 'h':80},
				'size':{'force_aspect':None, 'level':None, 'pct':None, 'is_full':True, 'w':None, 'h':None},
				'rotation':0
			},
			'rotation_exact' :{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/full/full/180/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'level':None, 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':180
			},
			'rotation_round_up' :{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/full/full/46/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'level':None, 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':90
			},
			'rotation_round_down' :{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/full/full/280/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'level':None, 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':270
			},
			'rotation_gt_314' :{ # would round to 360, which == 0
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/full/full/315/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'level':None, 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':0
			},
			# TODO: size and rotation
		}
		c = Client(self.app, BaseResponse)
		for q in pass_queries:
			resp = c.get(pass_queries[q]['uri'])
			status = resp.status_code
			self.assertEqual(status, 200, 'Query key "' + q + '" returned ' + str(status))
			elements = ast.literal_eval(resp.data)
			#	print elements
			fail_msg = 'Query key "' + q + '"\'s region params are unexpected'
			self.assertEqual(elements['region'], pass_queries[q]['region'], fail_msg)
			fail_msg = 'Query key "' + q + '"\'s size params unexpected'
			self.assertEqual(elements['size'], pass_queries[q]['size'], fail_msg)
			fail_msg = 'Query key "' + q + '"\'s rotation unexpected'
			self.assertEqual(elements['rotation'], pass_queries[q]['rotation'], fail_msg)
				
	def test_converter_exceptions(self):
		fail_queries = {
			'region_pct_fail':{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/pct:101,10,70,80/full/0/native.jpg',
				'raises': BadRegionSyntaxException
			},
			'region_syntax_fail':{
				'uri' :'/ctests/pudl0001/4609321/s42/00000004/NaN,10,70,80/full/0/native.jpg',
				'raises': BadRegionSyntaxException
			}
			# TODO: size (lots) and rotation
			# note that we still need rotation exceptions		
					
		}

		c = Client(self.app, BaseResponse)	
		for q in fail_queries:
			with self.assertRaises(fail_queries[q]['raises'],):
				c.get(fail_queries[q]['uri'])

	
	def test_img_info(self):
		# be sure to test content and XML and json validity
		pass 
		
