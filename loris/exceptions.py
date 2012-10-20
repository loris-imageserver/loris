#loris.exceptions.py
from loris.constants import IMG_API_NS
import xml.dom.minidom

class LorisException(Exception):
	"""Base exception class for Loris.

	The main feature is the `to_xml` method, which enable us to send back the
	error in the Response body, per IIIF 6.2

	See <http://www-sul.stanford.edu/iiif/image-api/#error>

	Attributes:
		http_status (int): the HTTP status the should be sent with the response.
		supplied_value (str): the parameter that caused the problem.
		msg (str): any additional info about what went wrong.
	"""
	def __init__(self, http_status=404, supplied_value='', msg=''):
		"""
		Kwargs:
			http_status (int): the HTTP status the should be sent with the 
				response.
			supplied_value (str): the parameter that caused the problem.
			msg (str): any additional info about what went wrong.
		"""
		super(LorisException, self).__init__(msg)
		self.http_status = http_status
		self.supplied_value = supplied_value

	def to_xml(self):
		"""Serialize the Exception to XML

		Return:
			str.
		"""
		doc = xml.dom.minidom.Document()
		error = doc.createElementNS(IMG_API_NS, 'error')
		error.setAttribute('xmlns', IMG_API_NS)
		doc.appendChild(error)

		parameter = doc.createElementNS(IMG_API_NS, 'parameter')
		parameter.appendChild(doc.createTextNode(self.supplied_value))
		error.appendChild(parameter)

		text = doc.createElementNS(IMG_API_NS, 'text')
		text.appendChild(doc.createTextNode(self.message))
		error.appendChild(text)
		return doc.toxml(encoding='UTF-8')

class BadRegionSyntaxException(LorisException): pass
class BadRegionRequestException(LorisException): pass
class BadSizeSyntaxException(LorisException): pass
class BadSizeRequestException(LorisException): pass
class BadRotationSyntaxException(LorisException): pass
