#!/usr/bin/env python

from patokah import create_app, BadSizeSyntaxException, BadRegionSyntaxException
from werkzeug.test import Client
from werkzeug.testapp import test_app
from werkzeug.wrappers import BaseResponse
import ast
import os
import unittest

class TestPatokah(unittest.TestCase):
	
	def setUp(self):
		unittest.TestCase.setUp(self)
		self.app = create_app(test=True)
	
	def test_converters(self):
		# queries are based on the examples in the region, rotation and size sections
		pass_queries = {
			'simple' :{
				# if my request is ...
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/0/native.jpg',
				# my converter responses should be ...
				'region' :{'is_pct':False, 'h':None, 'value':'full', 'is_full':True, 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':0
			},
			'region_pixels':{
				'uri' :'/pudl0001/4609321/s42/00000004/80,50,16,75/full/0/native.jpg',
				'region' :{'is_pct':False, 'is_full':False, 'value':'80,50,16,75', 'x':80, 'y':50, 'w':16, 'h':75},
				'size':{'force_aspect':None, 'value':'full', 'pct':None, 'is_full':True, 'w':None, 'h':None},
				'rotation':0
			},
			'region_pct':{
				'uri' :'/pudl0001/4609321/s42/00000004/pct:10,10,70,80/full/0/native.jpg',
				'region' :{'is_pct':True, 'is_full':False, 'value':'pct:10,10,70,80', 'x':10, 'y':10, 'w':70, 'h':80},
				'size':{'force_aspect':None, 'value':'full', 'pct':None, 'is_full':True, 'w':None, 'h':None},
				'rotation':0
			},
			'rotation_exact' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/180/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':180
			},
			'rotation_round_up' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/46/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':90
			},
			'rotation_round_down' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/280/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':270
			},
			'rotation_gt_314' :{ # would round to 360, which == 0
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/315/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':360
			},
			'negative_rotation' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/-92/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'h':None, 'value':'full', 'pct':None, 'is_full':True, 'w':None},
				'rotation':-90
			},
			'negative_rotation_lt_neg314' :{ # would round to 360, which == 0
				'uri' :'/pudl0001/4609321/s42/00000004/full/full/-315/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'value':'full', 'h':None, 'pct':None, 'is_full':True, 'w':None},
				'rotation':-360
			},
			'size_50_pct' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/pct:50/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'pct':50, 'value':'pct:50', 'is_full':False, 'w':None, 'h':None},
				'rotation':0
			},
			'size_100_w' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/100,/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'pct':None, 'value':'100,', 'is_full':False, 'w':100, 'h':None},
				'rotation':0
			},
			'size_100_h' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/,100/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':None, 'pct':None, 'value':',100', 'is_full':False, 'w':None, 'h':100},
				'rotation':0
			},
			'size_wh_forced' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/150,75/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':True, 'pct':None, 'value':'150,75', 'is_full':False, 'w':150, 'h':75},
				'rotation':0
			},
			'size_wh_unforced' :{
				'uri' :'/pudl0001/4609321/s42/00000004/full/!150,75/0/native.jpg',
				'region' :{'is_pct':False, 'h':None, 'is_full':True, 'value':'full', 'w':None, 'y':None, 'x':None},
				'size':{'force_aspect':False, 'pct':None, 'value':'!150,75', 'is_full':False, 'w':150, 'h':75},
				'rotation':0
			}
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
				# if my request is:
				'uri' :'/pudl0001/4609321/s42/00000004/pct:101,10,70,80/full/0/native.jpg',
				# ____ should be raised:
				'raises': BadRegionSyntaxException
			},
			'region_syntax_fail':{
				'uri' :'/pudl0001/4609321/s42/00000004/NaN,10,70,80/full/0/native.jpg',
				'raises': BadRegionSyntaxException
			},
			'lt_1_width_fail':{
				'uri' :'/pudl0001/4609321/s42/00000004/full/-2,/0/native.jpg',
				'raises': BadSizeSyntaxException
			},
			'lt_1_height_fail':{
				'uri' :'/pudl0001/4609321/s42/00000004/full/,-2/0/native.jpg',
				'raises': BadSizeSyntaxException
			},
			'upsample_pct_fail':{
				'uri' :'/pudl0001/4609321/s42/00000004/full/pct:101/0/native.jpg',
				'raises': BadSizeSyntaxException
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

if __name__ == "__main__":
	'Run the tests'
	unittest.main()
		
