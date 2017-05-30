#!/usr/bin/env python2
from scc.actions import Action, DPadAction, XYAction
from scc.modifiers import ModeModifier, DoubleclickModifier
from scc.parser import TalkingActionParser
from scc.constants import SCButtons
from scc.profile import Profile
from scc.tools import nameof
from scc.gui.svg_widget import SVGEditor
from scc.lib import IntEnum
import os


class Align(IntEnum):
	TOP  =    1 << 0
	BOTTOM =  1 << 1
	LEFT =    1 << 2
	RIGHT =   1 << 3


def find_image(name):
	# TODO: This
	filename = "images/" + name + ".svg"
	if os.path.exists(filename):
		return filename
	return None


class Line(object):
	
	def __init__(self, icon, text):
		self.icons = [ icon ]
		self.text = text
	
	
	def get_size(self, gen):
		# TODO: This
		return gen.char_width * len(self.text), gen.line_height
	
	
	def add_icon(self, icon):
		self.icons.append(icon)
		return self
	
	
	def to_string(self):
		return "%-10s: %s" % (",".join([ x for x in self.icons if x ]), self.text)


class LineCollection(object):
	""" Allows calling add_icon on multiple lines at once """
	
	def __init__(self, *lines):
		self.lines = lines
	
	
	def add_icon(self, icon):
		for line in self.lines:
			line.add_icon(icon)
		return self


class Box(object):
	PADDING = 5
	SPACING = 2
	MIN_WIDTH = 100
	MIN_HEIGHT = 50
	
	def __init__(self, anchor_x, anchor_y, align, name):
		self.name = name
		self.lines = []
		self.anchor = anchor_x, anchor_y
		self.align = align
		self.x, self.y = 0, 0
		self.width, self.height = self.MIN_WIDTH, self.MIN_HEIGHT
	
	
	def to_string(self):
		return "--- %s ---\n%s\n" % (
			self.name,
			"\n".join([ x.to_string() for x in self.lines ])
		)
	
	
	def add(self, icon, context, action):
		if not action: return LineCollection()
		if isinstance(action, ModeModifier):
			lines = [ self.add(icon, context, action.default) ]
			for x in action.mods:
				lines.append( self.add(nameof(x), context, action.mods[x])
						.add_icon(icon) )
			return LineCollection(*lines)
		elif isinstance(action, DoubleclickModifier):
			lines = []
			if action.normalaction:
				lines.append( self.add(icon, context, action.normalaction) )
			if action.action:
				lines.append( self.add("DOUBLECLICK", context, action.action)
						.add_icon(icon) )
			if action.holdaction:
				lines.append( self.add("HOLD", context, action.holdaction)
						.add_icon(icon) )
			return LineCollection(*lines)
		
		action = action.strip()
		if isinstance(action, DPadAction):
			return LineCollection(
				self.add("UP",    Action.AC_BUTTON, action.actions[0]),
				self.add("DOWN",  Action.AC_BUTTON, action.actions[1]),
				self.add("LEFT",  Action.AC_BUTTON, action.actions[2]),
				self.add("RIGHT", Action.AC_BUTTON, action.actions[3])
			)
		elif isinstance(action, XYAction):
			return LineCollection(
				self.add("AXISX",  Action.AC_BUTTON, action.x),
				self.add("AXISY",  Action.AC_BUTTON, action.y)
			)
		line = Line(icon, action.describe(context))
		self.lines.append(line)
		return line
	
	
	def calculate(self, gen):
		self.width, self.height = self.MIN_WIDTH, 2 * self.PADDING
		self.icount = 0
		for line in self.lines:
			lw, lh = line.get_size(gen)
			self.width, self.height = max(self.width, lw), self.height + lh + self.SPACING
			self.icount = max(self.icount, len(line.icons))
		self.width += 2 * self.PADDING + self.icount * (gen.line_height + self.SPACING)
		self.height = max(self.height, self.MIN_HEIGHT)
		
		anchor_x, anchor_y = self.anchor
		if (self.align & Align.TOP) != 0:
			self.y = anchor_y
		elif (self.align & Align.BOTTOM) != 0:
			self.y = gen.full_height - self.height - anchor_y
		else:
			self.y = (gen.full_height - self.height) / 2
		
		if (self.align & Align.LEFT) != 0:
			self.x = anchor_x
		elif (self.align & Align.RIGHT) != 0:
			self.x = gen.full_width - self.width - anchor_x
		else:
			self.x = (gen.full_width - self.width) / 2
	
	
	def place(self, gen, root):
		e = SVGEditor.add_element(root, "rect",
			style = "opacity:1;fill-color:#000000;fill-opacity:1.0;" +
				"fill-rule:evenodd;stroke:#06a400;stroke-width:0.5;",
			id = "box_%s" % (self.name,),
			width = self.width, height = self.height,
			x = self.x, y = self.y,
		)
		
		y = self.y + self.PADDING
		for line in self.lines:
			h = gen.line_height
			x = self.x + self.PADDING
			for icon in line.icons:
				image = find_image(icon)
				if image:
					SVGEditor.add_element(root, "image", x = x, y = y,
						width = h, height = h, href = image)
				x += h + self.SPACING
			x = self.x + self.PADDING + self.icount * (h + self.SPACING)
			y += h
			txt = SVGEditor.add_element(root, "text", x = x, y = y,
				style = gen.label_template.attrib['style']
			)
			SVGEditor.set_text(txt, line.text)
			y += self.SPACING
	
	
	def place_marker(self, gen, root):
		x1, y1 = self.x, self.y
		x2, y2 = x1 + self.width, y1 + self.height
		if self.align & (Align.LEFT | Align.RIGHT) == 0:
			edges = [ [ x1, y1 ], [ x2, y2 ],
					  [ x1, y2 ], [ x2, y1 ] ]
		else:
			edges = [ [ x1, y1 ], [ x2, y1 ],
					  [ x1, y2 ], [ x2, y2 ] ]
		
		targets = SVGEditor.get_element(root, "markers_%s" % (self.name,))
		if targets is None:
			return
		i = 0
		for target in targets:
			tx, ty = float(target.attrib["cx"]), float(target.attrib["cy"])
			i += 1
			try:
				edges[i] += [ tx, ty ]
			except IndexError:
				break
		edges = [ i for i in edges if len(i) == 4]
		
		for x1, y1, x2, y2 in edges:
			e = SVGEditor.add_element(root, "line",
				style = "opacity:1;stroke:#06a400;stroke-width:0.5;",
				# id = "box_%s_line0" % (self.name,),
				x1 = x1, y1 = y1, x2 = x2, y2 = y2
			)
		
	

class Generator(object):
	PADDING = 10
	
	def __init__(self):
		svg = SVGEditor(file("images/binding-display.svg").read())
		background = SVGEditor.get_element(svg, "background")
		self.label_template = SVGEditor.get_element(svg, "label_template")
		self.line_height = int(float(self.label_template.attrib.get("height") or 8))
		self.char_width = int(float(self.label_template.attrib.get("width") or 8))
		self.full_width = int(float(background.attrib.get("width") or 800))
		self.full_height = int(float(background.attrib.get("height") or 800))
		
		profile = Profile(TalkingActionParser()).load("test.sccprofile")
		boxes = []

		box_stick = box = Box(self.PADDING, self.PADDING, Align.LEFT | Align.BOTTOM, "stick")
		box.add("STICK", Action.AC_STICK, profile.stick)
		boxes.append(box)
		
		box_lpad = box = Box(self.PADDING, 0, Align.LEFT, "lpad")
		box.add("LPAD", Action.AC_PAD, profile.pads.get(profile.LEFT))
		boxes.append(box)
		
		
		box_rpad = box = Box(self.PADDING, 0, Align.RIGHT, "rpad")
		box.add("RPAD", Action.AC_PAD, profile.pads.get(profile.RIGHT))
		boxes.append(box)
		
		
		box_bcs = box = Box(0, self.PADDING, Align.TOP, "bcs")
		box.add("BACK", Action.AC_BUTTON, profile.buttons.get(SCButtons.BACK))
		box.add("C", Action.AC_BUTTON, profile.buttons.get(SCButtons.C))
		box.add("START", Action.AC_BUTTON, profile.buttons.get(SCButtons.START))
		boxes.append(box)
		
		
		box_left =box = Box(self.PADDING, self.PADDING, Align.LEFT | Align.TOP, "left")
		box.add("LTRIGGER", Action.AC_TRIGGER, profile.triggers.get(profile.LEFT))
		box.add("LB", Action.AC_BUTTON, profile.buttons.get(SCButtons.LB))
		box.add("LGRIP", Action.AC_BUTTON, profile.buttons.get(SCButtons.LGRIP))
		boxes.append(box)
		
		
		box_right = box = Box(self.PADDING, self.PADDING, Align.RIGHT | Align.TOP, "right")
		box.add("RTRIGGER", Action.AC_TRIGGER, profile.triggers.get(profile.RIGHT))
		box.add("RB", Action.AC_BUTTON, profile.buttons.get(SCButtons.RB))
		box.add("RGRIP", Action.AC_BUTTON, profile.buttons.get(SCButtons.RGRIP))
		boxes.append(box)
		
		
		box_abxy = box = Box(self.PADDING, self.PADDING, Align.RIGHT | Align.BOTTOM, "abxy")
		box.add("A", Action.AC_BUTTON, profile.buttons.get(SCButtons.A))
		box.add("B", Action.AC_BUTTON, profile.buttons.get(SCButtons.B))
		box.add("X", Action.AC_BUTTON, profile.buttons.get(SCButtons.X))
		box.add("Y", Action.AC_BUTTON, profile.buttons.get(SCButtons.Y))
		boxes.append(box)
		
		
		w = int(float(background.attrib.get("width") or 800))
		h = int(float(background.attrib.get("height") or 800))
		
		root = SVGEditor.get_element(svg, "root")
		for b in boxes:
			b.calculate(self)
		
		self.fix_width(box_left, box_lpad, box_stick)
		self.distribute_height(box_left, box_lpad, box_stick)
		
		for b in boxes:
			b.place(self, root)
			b.place_marker(self, root)
		
		file("out.svg", "w").write(svg.to_string())
	
	
	def fix_width(self, *boxes):
		""" Sets width of all passed boxes to width of widest box """
		width = 0
		for b in boxes: width = max(width, b.width)
		for b in boxes: b.width = width


	def distribute_height(self, *boxes):
		"""
		Distributes available height between specified boxes, ensuring that
		box with many lines gets enough space and there is no empty space in
		between
		"""
		height = self.full_height - (2 + len(boxes)) *self.PADDING
		occupied = sum([ b.height for b in boxes ])
		rest = height - occupied
		
		if rest > 0:
			for b in boxes:
				b.height += rest / len(boxes)
				if b.align & Align.BOTTOM != 0:
					b.y -= rest / len(boxes)
				elif b.align & Align.TOP == 0:
					# aligned to center
					b.y -= rest / len(boxes) / 2


Generator()
