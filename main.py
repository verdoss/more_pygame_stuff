from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import numpy
from PIL import Image

import font
import color
import tile
import unit
import tooltips
import random
import coord
import pathfinding
import tex
import fps
import geometry

# TODO: next step, implement turn structure.

window = 0		# glut window number

TILE_TYPE = tile.RECT
MAP_SIZE = coord.Coord(x=10, y=10)
WINDOW_SIZE = coord.Coord(x=640, y=480)
FULLSCREEN = False
USEFONT = False
USETEX = TILE_TYPE == tile.RECT
TEXDIR = "textures/"
TEXEXT = ".png"
RANDRANGE=(1,3)
SHOWFPS=True


TILE_ADJ = [
	coord.Coord(x=-1,y= 0),
	coord.Coord(x= 0,y=-1),
	coord.Coord(x= 1,y= 0),
	coord.Coord(x= 0,y= 1)
]

ARROW_ROT = {
	( 0, 1): 0,
	(-1, 0): 1,
	( 0,-1): 2,
	( 1, 0): 3
}

CORNER_ROT = {
	(-1, 0, 0, 1): 1,
	( 0, 1,-1, 0): 3,
	
	(-1, 0, 0,-1): 0,
	( 0,-1,-1, 0): 2,
	
	( 1, 0, 0,-1): 3,
	( 0,-1, 1, 0): 1,
	
	( 1, 0, 0, 1): 2,
	( 0, 1, 1, 0): 0
}


#g_TILETEX =  if TILE_TYPE == tile.RECT else "hex-bound"
g_texnames = [key for key in tex.ATLAS_POSITIONS]

def refresh2d(vw, vh, width, height):
	glViewport(0, 0, width, height)
	glClearColor(0, 0, 0, 0)
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho(0.0, vw, 0.0, vh, 0.0, 1.0)
	glMatrixMode (GL_MODELVIEW)
	glLoadIdentity()

class mygame:
	def __init__(self):
		random.seed(None)
		
		self.window_size = WINDOW_SIZE
		self.map_size = MAP_SIZE
		self.size = (1.0 / self.map_size.x, 1.0 / self.map_size.y)
		self.selected = None
		
		#self.tiles = []
		self.m_d_v2_tiles = {}
		for y in range(self.map_size.y):
			for x in range(self.map_size.x):
				ttex = 0#g_texnames.index(g_TILETEX)#(x+y*self.map_size.x)%2
				tx = x if TILE_TYPE == tile.RECT else (x + (0.5 if y%2 == 0 else 0.0))
				ty = y
				tloc = coord.Coord(x=tx, y=ty)
				tweight = random.randint(RANDRANGE[0], RANDRANGE[1])
				#self.tiles.append(tile.tile(tx, ty, ttex, TILE_TYPE, tweight))
				self.m_d_v2_tiles[tloc] = tile.tile(tx, ty, ttex, TILE_TYPE, tweight)
		self.init_window()
		self.init_callback()
		tex.init()
		self.units = {
			coord.Coord(x=0,y=0): unit.unit(coord.Coord(x=0,y=0), g_texnames.index("unit"), 2),# * sum(RANDRANGE)/2),
			coord.Coord(x=4,y=6): unit.unit(coord.Coord(x=4,y=6), g_texnames.index("unit"), 4),# * sum(RANDRANGE)/2),
			coord.Coord(x=3,y=6): unit.unit(coord.Coord(x=3,y=6), g_texnames.index("unit"), 1),# * sum(RANDRANGE)/2),
			coord.Coord(x=3,y=5): unit.unit(coord.Coord(x=3,y=5), g_texnames.index("unit"), 0),# * sum(RANDRANGE)/2)
		}
		self.selected = None
		self.mouseloc = None
		self.wmouseloc = None
		self.l_v2_movereg = None # TODO: REPLACE WITH PATH SUPERSET.
		self.tooltip = tooltips.tooltip(1.0)
		self.tooltip.start()
		self.path = None
		self.myfps = fps.fps()
	def init_window(self):
		glutInit()
		glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
		glutInitWindowSize(self.window_size.x, self.window_size.y)
		glutInitWindowPosition(0, 0)
		self.window = glutCreateWindow(b'Hello World!')
		if FULLSCREEN: glutFullScreen()
	def init_callback(self):
		glutDisplayFunc(lambda: self.draw())
		glutIdleFunc(lambda: self.draw())
		glutMouseFunc(lambda button, state, x, y: self.mouse(button, state, x, y))
		glutPassiveMotionFunc(lambda x, y: self.mouse_passive(x, y))
		glutKeyboardFunc(lambda key, x, y: self.keyboard(key, x, y))
		glutReshapeFunc(lambda w, h: self.reshape(w, h))
	
	def get_delta(self, v2_s, v2_d):
		if v2_s[0] > v2_d[0]:
			return (-1, 0)
		elif v2_s[0] < v2_d[0]:
			return ( 1, 0)
		elif v2_s[1] > v2_d[1]:
			return ( 0,-1)
		else:# v2_s[0] < v2_d[0]:
			return ( 0, 1)
	def deltas_to_tex(self, delta_src, delta_dst):
		if delta_src == delta_dst:
			rot = ARROW_ROT[(delta_src.x,delta_src.y)]
		else:
			rot = CORNER_ROT[(delta_src.x,delta_src.y)+(delta_dst.x,delta_dst.y)]
		if delta_dst.x == delta_src.x or delta_dst.y == delta_src.y:
			texname = "arrow-ud"
		else:
			texname = "arrow-ur"
			
		return (g_texnames.index(texname), rot)
	def get_path_tex(self, v2_s, v2_d, r):
		#def get_path(d_graph, src, max_weight, deltas):
		print("enter get_path_tex:", v2_s, v2_d)
		if v2_d == v2_s:
			return {}
		tiles = {}
		# todo: create a more sparse weight dict
		for tloc in self.m_d_v2_tiles:
			if not tloc in self.units:
				tiles[tloc] = self.m_d_v2_tiles[tloc].weight
		path = pathfinding.get_path(tiles, v2_s, r, TILE_ADJ)
		# path dict [coordinate tuple] : .src(delta), .weight
		n = 0
		for key in path:
			n += 1
		print("test:",n,v2_d,v2_s)
		if not v2_d in path or not v2_s in path:
			return {}
			
		v2_t = v2_d
		rdict = {v2_t:(g_texnames.index("arrow-u"), ARROW_ROT[path[v2_t].delta])}
		
		while v2_t - path[v2_t].delta != v2_s:
			nextdelta = path[v2_t - path[v2_t].delta].delta
			delta = path[v2_t].delta
			
			rdict[v2_t - delta] = self.deltas_to_tex(nextdelta, delta)
			v2_t = v2_t - delta
		return rdict
		
	def coord_in_bounds(self, v2_c):
		return v2_c[0] >= 0 and v2_c[1] >= 0 and v2_c[0] < self.map_size.x and v2_c[1] < self.map_size.y
	def get_range_list(self, v2_s, r):
		
		tiles = {}
		for tloc in self.m_d_v2_tiles:
			if not tloc in self.units:
				tiles[tloc] = self.m_d_v2_tiles[tloc].weight
		return [loc for loc in pathfinding.get_path(tiles, v2_s, r, TILE_ADJ)]
		"""
		# TODO: include path to each cell.
		# (combine with get_path_tex)
		a_targ = [[] for i in range(r+1)]
		a_targ[0].append(v2_s)
		for i in range(1,r+1):
			for v2_tile in a_targ[i-1]:
				for v2_delta in TILE_ADJ:
					v2_coord = (v2_tile[0]+v2_delta[0], v2_tile[1]+v2_delta[1])
					if self.coord_in_bounds(v2_coord) and not self.loc_has_unit(v2_coord):
						for l in a_targ:
							if v2_coord in l:
								break
						else:
							a_targ[i].append(v2_coord)
		return a_targ
		"""
	
	def reshape(self, w, h):
		self.window_size.x = w
		self.window_size.y = h
	def mouse_passive(self, x, y):
		self.wmouseloc = coord.Coord(x=x,y=y)
		self.wmouseloc *= coord.Coord(x=1.0,y=-1.0)
		self.wmouseloc += coord.Coord(x=0,y=self.window_size.y-1)
		self.wmouseloc /= self.window_size
		
		nx = x * self.map_size.x // self.window_size.x
		ny = (self.window_size.y - y) * self.map_size.y // self.window_size.y
		
		self.mouseloc = coord.Coord(x=nx,y=ny)
		
		if self.selected != None:
			self.update_path()
		if self.mouseloc in self.m_d_v2_tiles:
			self.tooltip.data = self.m_d_v2_tiles[self.mouseloc].weight
			self.tooltip.start()
	def mouse(self, button, state, x, y):
		# TODO: ADD HEX CLICK LOGIC.
		if TILE_TYPE != tile.RECT: return
		rx = x * self.map_size.x // self.window_size.x
		ry = (self.window_size.y - y) * self.map_size.y // self.window_size.y
		ri = ry * self.map_size.x + rx
		if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
			if coord.Coord(x=rx,y=ry) in self.units:
				self.selected = coord.Coord(x=rx,y=ry)
				self.l_v2_movereg=self.get_range_list(self.units[self.selected].loc, self.units[self.selected].moverange)
				self.update_path()
			else:
				self.selected = None
				self.update_path()
				self.l_v2_movereg = None
		elif button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
			c = coord.Coord(x=rx,y=ry)
			if self.l_v2_movereg != None and c in self.l_v2_movereg and not c in self.units:
				self.units[c] = self.units[self.selected]
				self.units.pop(self.selected, None)
				self.selected = c
				self.units[self.selected].loc = self.selected
				self.l_v2_movereg = self.get_range_list(self.selected, self.units[self.selected].moverange)
				self.update_path()
	def update_path(self):
		if self.selected == None or self.mouseloc == None:
			self.path = None
		else:
			self.path = self.get_path_tex(self.selected, self.mouseloc, self.units[self.selected].moverange)
	def keyboard(self, key, x, y):
		if key == b'\x1b':
			self.tooltip.stop()
			exit()
	
	def get_range(self, l2_range, v2_coord):
		if l2_range == None:
			return -1
		for i in range(len(l2_range)):
			if v2_coord in l2_range[i]:
				return i
		return -1
	def get_tile_tex(self, t):
		for u in self.units:
			if u.loc == t.loc:
				return u.tex
		else:
			return t.tex
	def loc_has_unit(self, loc):
		return loc in self.units
	def draw(self):
		refresh2d(1, 1, self.window_size.x, self.window_size.y)										# set mode to 2d
		
		#glClear(GL_COLOR_BUFFER_BIT)
		glEnable(GL_TEXTURE_2D)
	
		glBindTexture(GL_TEXTURE_2D, tex.g_texture)
		for loc in self.m_d_v2_tiles:
			stex = "unit" if loc in self.units else "bound"
			rot = 0
			#r = self.get_range(self.l_v2_movereg, loc)
			
			if self.l_v2_movereg == None or not loc in self.l_v2_movereg: # tile is not in range of selected unit
				if self.mouseloc != None and loc == self.mouseloc:
					c = color.d_color["BLUE"]
				else:
					c = color.d_color["WHITE"]
			elif self.loc_has_unit(loc) and (self.selected == None or loc != self.units[self.selected].loc):
				c = color.d_color["WHITE"]
			else:
				c = color.d_color["RED"]
			weightmult = ((self.m_d_v2_tiles[loc].weight - RANDRANGE[0] + 1.0) / (RANDRANGE[1] - RANDRANGE[0] + 1.0))
			#weightmult for an appropriate RANDRANGE should be [W+1/dR+1 for W] -> [1/2,2/2] for dR=1
			c = c * weightmult
			c.draw()
			self.m_d_v2_tiles[loc].draw(self.size, rot, tex.get_texcoords(stex, rot))
			
			if self.path != None and loc in self.path:
				itex, rot = self.path[loc]
				(color.d_color["WHITE"]*0.5).draw()
				self.m_d_v2_tiles[loc].draw(self.size, rot, tex.get_texcoords(g_texnames[itex], rot))
			#"""
		glDisable(GL_TEXTURE_2D)
		if self.tooltip.do_render and self.wmouseloc != None:
			s = "data: " + repr(self.tooltip.data)
			font.draw(s, self.wmouseloc[0], self.wmouseloc[1] + 3.0 / self.window_size.y, True, self.window_size, self.size)
		if SHOWFPS:
			self.myfps.update()
			self.myfps.draw((0.0,0.0), self.window_size, self.size)
		glutSwapBuffers()
		
# initialization
geometry.TILETYPE = geometry.RECT
m = mygame()

glutMainLoop() # start everything