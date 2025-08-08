#################################################################################
#
#    Plugin for Enigma2, control fan in edision osmega
#
#    Coded by ims (c)2025, version 1.0.4
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
from Tools.Directories import fileCheck

def main(session,**kwargs):
	if fileCheck("/proc/stb/fp/fan"):
		from . import ui
		session.open(ui.AutoFanSetup)
	else:
		from Screens.MessageBox import MessageBox
		session.open(MessageBox, _("No controllable fan exists on this box!"), type=MessageBox.TYPE_ERROR)

def sessionstart(reason, **kwargs):
	if reason == 0:
		if fileCheck("/proc/stb/fp/fan"):
			from . import ui
			ui.AutoFan.startAutoFan()
		else:
			print("[AutoFan] No fan device found on this box, plugin not started.")

def Plugins(**kwargs):
	name = "AutoFan"
	descr = _("Controls Edision OsMega fan.")
	return [
		PluginDescriptor(name=name, description=descr, where=PluginDescriptor.WHERE_PLUGINMENU, icon = 'plugin.png', fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart = True),
	]
