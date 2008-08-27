#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright © 2008 Can Berk Güder <cbguder@su.sabanciuniv.edu>
#
# This file is part of TSense Screenlet.
#
# TSense Screenlet is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# TSense Screenlet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TSense Screenlet; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  
# USA

import screenlets
from screenlets.options import BoolOption, ColorOption, IntOption, ListOption
import cairo
import pango
import subprocess
import re
import gobject
import os

WIDTH         = 220
SENSOR_HEIGHT = 27
PADDING       = 12

def get_sensors():
	data = {}
	sensors = os.popen('sensors')
	for line in sensors:
		parts = line.split(':')
		if len(parts) > 1:
			value = parts[1].split()[0]
			if value[-1] == 'C':
				type = 'Temperature'
				value = value[1:-3]
			else:
				type = 'RPM'
			try:
				value = float(value)
			except:
				pass
			else:
				data[parts[0]] = {'name': parts[0], 'value': value, 'type': type }
	sensors.close()
	return data

class TSenseScreenlet(screenlets.Screenlet):
	"""A screenlet that displays information from sensors."""
	
	# default meta-info for Screenlets
	__name__ = 'TSenseScreenlet'
	__version__ = '0.1'
	__author__ = 'Can Berk Güder'
	__desc__ = __doc__

	# internals
	__timeout = None
	p_layout = None	

	# settings
	update_interval = 2
	sensors         = ['CPU Fan', 'Case Fan', 'Sys Temp', 'CPU Temp', 'Core 0', 'Core 1']
	color_normal    = (0.0, 1.0, 0.0, 1.0)
	color_warning   = (1.0, 1.0, 0.0, 1.0)
	color_alarm     = (1.0, 0.0, 0.0, 1.0)
	color_text      = (0.0, 0.0, 0.0, 0.6)
	frame_color     = (1.0, 1.0, 1.0, 1.0)

	# constructor
	def __init__(self, **keyword_args):
		#call super
		screenlets.Screenlet.__init__(self, width=WIDTH, height=SENSOR_HEIGHT * len(self.sensors) + 2 * PADDING, uses_theme=True, **keyword_args)
		# set theme
		self.theme_name = 'default'
		# add options
		self.add_options_group('TSense', 'TSense specific options')
		self.add_option(IntOption('TSense', 'update_interval', 
			self.update_interval, 'Update Interval', 
			'The interval for updating sensor data (in seconds) ...',
			min=1, max=60))
		self.add_option(ListOption('TSense', 'sensors',
			self.sensors, 'Sensors',
			'List of sensors you want to display'))
		self.add_option(ColorOption('TSense', 'color_normal',
			self.color_normal, 'Normal Color',
			'The color to be displayed when drive usage is below the threshold'))
		self.add_option(ColorOption('TSense', 'color_warning',
			self.color_warning, 'Warning Color',
			'The color to be displayed when drive usage is below the threshold'))
		self.add_option(ColorOption('TSense', 'color_alarm',
			self.color_alarm, 'Alarm Color',
			'The color to be displayed when drive usage is below the threshold'))
		self.add_option(ColorOption('TSense', 'color_text', self.color_text, 'Text Color', ''))
		self.add_option(ColorOption('TSense', 'frame_color', self.frame_color, 'Frame Color', ''))

		# init the timeout function
		self.update_interval = self.update_interval

	def on_init(self):
		print "Screenlet has been initialized."
		# add default menu items
		self.add_default_menuitems()
	
	def __setattr__(self, name, value):
		screenlets.Screenlet.__setattr__(self, name, value)

		if name == 'update_interval':
			if value <= 0:
				value = 1

			self.__dict__['update_interval'] = value

			if self.__timeout:
				gobject.source_remove(self.__timeout)

			self.__timeout = gobject.timeout_add(int(value * 1000), self.update_graph)
		elif name == 'sensors':
			self.width  = 230
			self.height = SENSOR_HEIGHT * len(value) + 2 * PADDING
			self.__dict__['sensors'] = value
			self.update_graph()
		else:
			self.update_graph()
	
	# timeout-function
	def update_graph(self):
		self.redraw_canvas()
		return True
	
	def on_draw(self, ctx):
		sensors = get_sensors()

		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)

		gradient = cairo.LinearGradient(0, self.height*2,0, 0)
		gradient.add_color_stop_rgba(1,*self.frame_color)
		gradient.add_color_stop_rgba(0.7,self.frame_color[0],self.frame_color[1],self.frame_color[2],1-self.frame_color[3]+0.5)
		ctx.set_source(gradient)
		self.draw_rectangle_advanced (ctx, 0, 0, self.width-12, self.height-12, rounded_angles=(5,5,5,5), fill=True, border_size=2, border_color=(0,0,0,0.5), shadow_size=6, shadow_color=(0,0,0,0.5))

		ctx.translate(PADDING, PADDING)
		for key in self.sensors:
			if sensors.has_key(key):
				self.draw_sensor(ctx, sensors[key])
			else:
				self.draw_sensor(ctx, {'name': key, 'type': None})
			ctx.translate(0, SENSOR_HEIGHT)	

	def draw_sensor(self, ctx, sensor):
		# draw text
		ctx.save()

		if self.p_layout == None :
			self.p_layout = ctx.create_layout()
		else:
			ctx.update_layout(self.p_layout)

		p_fdesc = pango.FontDescription()
		p_fdesc.set_family_static("Free Sans")
		p_fdesc.set_size(10 * pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)

		if sensor['type'] == 'Temperature':
			markup = "<b>%(name)s:</b> %(value).1f°C" % sensor
		elif sensor['type'] == 'RPM':
			markup = "<b>%(name)s:</b> %(value)d RPM" % sensor
		elif sensor['type'] == None:
			markup = "<b>%(name)s:</b> N/A" % sensor

		self.p_layout.set_markup(markup)
		apply(ctx.set_source_rgba, self.color_text)
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()
		ctx.save()

		apply(ctx.set_source_rgba, self.color_normal)

		if sensor['type'] == 'Temperature':
			warning = 50.0
			alarm   = 60.0
			max     = alarm

			if sensor['value'] > alarm:
				apply(ctx.set_source_rgba, self.color_alarm)
			elif sensor['value'] > warning:
				apply(ctx.set_source_rgba, self.color_warning)
		elif sensor['type'] == 'RPM':
			warning = 1200.0
			alarm   =  600.0
			max     = 3000.0

			if sensor['value'] < alarm or sensor['value'] > max:
				apply(ctx.set_source_rgba, self.color_alarm)
			elif sensor['value'] < warning:
				apply(ctx.set_source_rgba, self.color_warning)

		if sensor['type'] == None:
			w = 0.0
		else:
			w = 1.0 * WIDTH * sensor['value'] / max
		ctx.rectangle(0, 16, w, 6)
		ctx.fill()

	def on_draw_shape(self, ctx):
		ctx.rectangle(0, 0, 230 * self.scale, ((len(self.sensors) * SENSOR_HEIGHT) + 2 * PADDING) * self.scale)
		ctx.fill()
	
# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(TSenseScreenlet)
