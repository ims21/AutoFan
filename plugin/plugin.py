#################################################################################
#
#    Plugin for Enigma2, control fan in edision osmega
#
#    Coded by ims (c)2025, version 1.0.3
#    
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#################################################################################

from . import _
from Plugins.Plugin import PluginDescriptor

def main(session,**kwargs):
	from . import ui
	session.open(ui.AutoFanSetup)

def sessionstart(reason, **kwargs):
	if reason == 0:
		from . import ui
		ui.AutoFan.startAutoFan()

def Plugins(**kwargs):
	name = "AutoFan"
	descr = _("Controls Edision OsMega fan.")
	return [
		PluginDescriptor(name=name, description=descr, where=PluginDescriptor.WHERE_PLUGINMENU, icon = 'plugin.png', fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart = True),
	]
