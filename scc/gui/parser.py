from __future__ import unicode_literals
from scc.actions import ActionParser, ParseError
from scc.tools import _

class InvalidAction(object):
	def __init__(self, string, error):
		self.string = string
		self.error = error
	
	
	def to_string(self, *a):
		return self.string
	
	def describe(self, *a):
		return _("(invalid)")


class GuiActionParser(ActionParser):
	"""
	ActionParser that stores original string and
	returns InvalidAction instance when parsing fails
	"""
	
	def restart(self, string):
		self.string = string
		return ActionParser.restart(self, string)

	
	def parse(self):
		"""
		Returns parsed action or None if action cannot be parsed.
		"""
		try:
			a = ActionParser.parse(self)
			a.string = self.string
			return a
		except ParseError, e:
			return InvalidAction(self.string, e)
