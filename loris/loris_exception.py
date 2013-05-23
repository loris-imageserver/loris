class LorisException(Exception):
	"""Base exception class for Loris.

	See <http://www-sul.stanford.edu/iiif/image-api/#error>

	Attributes:
		http_status (int): the HTTP status the should be sent with the response.
		supplied_value (str): the parameter that caused the problem.
		msg (str): any additional info about what went wrong.
	"""
	def __init__(self, http_status, message, supplied_value=''):
		"""
		Kwargs:
			http_status (int): the HTTP status the should be sent with the 
				response.
			msg (str): any additional info about what went wrong.
			supplied_value (str): the parameter that caused the problem.
		"""
		super(LorisException, self).__init__(message)
		self.http_status = http_status
		self.supplied_value = supplied_value