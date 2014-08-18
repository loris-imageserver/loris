#-*- coding: utf-8 -*-

import loris_t
from PIL.ImageFile import Parser
from cStringIO import StringIO

"""
Transformer tests. These right now these work with the kakadu and PIL 
transformers. More should be added when different libraries/scenarios are added.

To run this test on its own, do:

$ python -m unittest tests.transforms_t

from the `/loris` (not `/loris/loris`) directory.
"""

class Test_KakaduJP2Transformer(loris_t.LorisTest):

    def test_allows_jp2_upsample(self):
        # Makes a request rather than building everything from scratch
        ident = self.test_jp2_color_id
        request_path = '/%s/full/pct:110/0/default.jpg' % (ident,)
        resp = self.client.get(request_path)

        self.assertEqual(resp.status_code, 200)

        image = None
        bytes = StringIO(resp.data)
        p = Parser()
        p.feed(bytes.read()) # all in one gulp!
        image = p.close()
        bytes.close()
        expected_dims = tuple(int(d*1.10) for d in self.test_jp2_color_dims)
        
        self.assertEqual(expected_dims, image.size)

def suite():
    import unittest
    test_suites = []
    test_suites.append(unittest.makeSuite(Test_KakaduJP2Transformer, 'test'))
    test_suite = unittest.TestSuite(test_suites)
    return test_suite
