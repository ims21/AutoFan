#################################################################################
#
#    Plugin for Enigma2, control fan in edision osmega
#
#    Coded by ims (c)2025, version 1.0.0
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
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigSubsection, config, ConfigSelection
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from enigma import eTimer, getDesktop
from enigma import eSize, ePoint
from Components.Pixmap import Pixmap

desktop = getDesktop(0)
Width = desktop.size().width()
Height = desktop.size().height()
fullHD = False
if Width > 1280:
	fullHD = True

config.plugins.autofan = ConfigSubsection()
choicelist = []
for i in range(35, 70, 1):
	choicelist.append(("%d" % i, "%d\u00b0C" % i))
config.plugins.autofan.temperature = ConfigSelection(default="50", choices=choicelist)
choicelist = []
for i in range(5, 125, 5):
	choicelist.append(("%d" % i, _("%d secs") % i))
config.plugins.autofan.refresh = ConfigSelection(default="10", choices=choicelist)
cfg = config.plugins.autofan

class AutoFanSetup(Screen, ConfigListScreen):
	skin = """
	<screen name="AutoFanSetup" position="center,center" size="560,180" title="AutoFan" >
		<widget name="red"    position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on"/>
		<widget name="green"  position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on"/>
		<widget name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on"/>
		<widget name="blue"   position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on"/>
		<widget name="key_red"    position="0,0"   size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2"/>
		<widget name="key_green"  position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2"/>
		<widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2"/>
		<widget name="key_blue"   position="420,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2"/>
		<widget name="config" position="10,45" size="540,125" zPosition="1" scrollbarMode="showOnDemand"/>
		<widget name="description" position="10,200" size="540,25" zPosition="1"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["AutoFanSetup", "Setup"]

		self.AutoFanRefreshTimer = eTimer()
		self.AutoFanRefreshTimer.timeout.get().append(self.refreshTemperature)

		self.list = [ ]
		self.onChangedEntry = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

#		self["key_green"] = StaticText(_("Ok"))
		self["key_red"] = StaticText(_("Cancel"))
		self["red"] = Pixmap()
#		self["green"] = Pixmap()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
#				"ok": self.ok,
#				"green": self.ok,
				"red": self.quit,
				"cancel": self.quit,
			}, -2)

		self["description"] = Label()
		self.fanmode = _("Fan mode")
		self.temperature = _("Temperature")
		self.refresh = _("Refresh time")
		self.onLayoutFinish.append(self.layoutFinished)

	def listMenu(self):
		self.list = [(self.fanmode, config.usage.fan)]
		if config.usage.fan.value == "auto":
			self.list.append((self.temperature, cfg.temperature))
			self.list.append((self.refresh, cfg.refresh))
		self["config"].setList(self.list)

	def changedEntry(self):
		if self["config"].getCurrent()[0] == self.fanmode:
			print("[AutoFan] fan mode changed to:", config.usage.fan.value)
			self.listMenu()
		#if self["config"].getCurrent()[0] == self.fanmode:
		#	pass
		#if self["config"].getCurrent()[0] == self.refresh:
		#	pass
		AutoFan.startAutoFan(self.session)

	def layoutFinished(self):
		self.listMenu()
		self.refreshTemperature()

	def refreshTemperature(self):
		temperature = AutoFan.getTemperature()
		if temperature is not None:
			self.setTitle(_("AutoFan") + " - " + _("temperature: %d\u00b0C" % temperature))
		else:
			self.setTitle(_("AutoFan") + " - " + _("unknown temperature"))
		self.AutoFanRefreshTimer.start(1000, True)
	
	def quit(self):
		cfg.save()
		config.usage.fan.save()
		AutoFan.startAutoFan(self.session)
		self.close()


class AutoFanMain():
	def __init__(self):
		self.AutoFanTimers = eTimer()
		self.AutoFanTimers.timeout.get().append(self.refreshTemp)

	def startAutoFan(self, session):
		self.session = session
		if config.usage.fan.value == "auto":
			self.AutoFanTimers.start(10000, True) # wait 10s on start enigma2

	def getTemperature(self):
		try:
			with open("/proc/stb/fp/temp_sensor_avs", "r") as f:
				temp = f.read().strip()
				return int(temp)
		except:
			return None

	def getFanMode(self):
		try:
			with open("/proc/stb/fp/fan", "r") as f:
				mode = f.read().strip()
				return mode
		except:
			return None

	def setFanMode(self, mode):
		if mode not in ("auto", "on", "off"):
			raise ValueError("Wrong fan mode!")
		try:
			with open("/proc/stb/fp/fan", "w") as f:
				f.write(mode)
			return True
		except Exception as e:
			print("Error write to %s: %s" % ("/proc/stb/fp/fan", e))
			return False

	def refreshTemp(self):
		#print("[AutoFan] mode: %s, temperature: %s, refresh: %s sec", config.usage.fan.value, cfg.temperature.value, cfg.refresh.value)
		mode = self.getFanMode
		if config.usage.fan.value == "on" and mode != "on":
			self.setFanMode("on")
		elif config.usage.fan.value == "off" and mode != "off":
			self.setFanMode("off")
		else: # auto
			temperature = self.getTemperature()
			if temperature is not None:
				print("[AutoFan] temperature: %d\u00b0C" % temperature)
				if temperature > int(cfg.temperature.value):
					self.setFanMode("auto")
				else:
					self.setFanMode("off")
			else:
				print("[AutoFan] cannot read temperature")
			self.AutoFanTimers.start(int(cfg.refresh.value) * 1000, True)

AutoFan = AutoFanMain()