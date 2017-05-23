class coord:
	def __init__(self, x, y):
		self.x, self.y = x, y
	def __add__(self, other):
		return coord(self.x+other.x, self.y+other.y)
	def __eq__(self, other):
		return self.x==other.x and self.y==other.y