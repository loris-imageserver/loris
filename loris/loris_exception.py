class LorisException(Exception):
	"""Base exception class for Loris.

	See <http://www-sul.stanford.edu/iiif/image-api/#error>

	Attributes:
		http_status (int): the HTTP status the should be sent with the response.
		supplied_value (str): the parameter that caused the problem.
		msg (str): any additional info about what went wrong.
	"""
	def __init__(self, http_status=400, message=''):
		"""
		Kwargs:
			http_status (int): the HTTP status the should be sent with the
				response.
			msg (str): any additional info about what went wrong.
			supplied_value (str): the parameter that caused the problem.
		"""
		# message = '%s: %s (%d)' % (self.__class__.__name__, message, http_status)
		super(LorisException, self).__init__(message)
		self.http_status = http_status

class SyntaxException(LorisException): pass
class RequestException(LorisException): pass
class ImageException(LorisException): pass
class ImageInfoException(LorisException): pass
class ResolverException(LorisException): pass
class TransformException(LorisException): pass
