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
from Screens.Screen import Screen
from Screens.Setup import getConfigMenuItem
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigSubsection, config, ConfigSelection, ConfigYesNo
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from enigma import eTimer, getDesktop
from Components.Pixmap import Pixmap
from time import strftime

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
	choicelist.append(("%d" % i, _("%d s") % i))
config.plugins.autofan.refresh = ConfigSelection(default="10", choices=choicelist)
cfg = config.plugins.autofan
config.plugins.autofan.log = ConfigYesNo(default=False)

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

		self["key_red"] = StaticText(_("Cancel"))
		self["red"] = Pixmap()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"red": self.quit,
				"cancel": self.quit,
			}, -2)

		self["description"] = Label()
		self.onLayoutFinish.append(self.layoutFinished)

	def listMenu(self):
		self.list = [getConfigMenuItem("config.usage.fan")]
		if config.usage.fan.value == "auto":
			self.list.append((_("Temperature"), cfg.temperature, _("The fan turns off when the set temperature is reached.")))
			self.list.append((_("Check interval"), cfg.refresh, _("Interval for temperature evaluation to control the fan.")))
			self.list.append((_("Log to file"), cfg.log, _("Log time, fan state and temperatures to a file during each 5 second. Turning off and on will overwrite the /tmp/autofan.log file.")))
		self["config"].setList(self.list)

	def changedEntry(self):
		if self["config"].getCurrent()[1] is config.usage.fan:
			print("[AutoFan] fan mode changed to:", config.usage.fan.value)
			self.listMenu()
		#if self["config"].getCurrent()[1] == cfg.temperature:
		#	pass
		#if self["config"].getCurrent()[1] == cfg.refresh:
		#	pass
		if self["config"].getCurrent()[1] == cfg.log:
			if cfg.log.value:
				AutoFan.header2Log()
		AutoFan.startAutoFan()

	def layoutFinished(self):
		self.listMenu()
		self.refreshTemperature()

	def refreshTemperature(self):
		temperature = AutoFan.getTemperature()
		if temperature is not None:
			self.setTitle(_("AutoFan") + " - " + _("temperature: %d%sC") % (temperature, chr(176)))
		else:
			self.setTitle(_("AutoFan") + " - " + _("unknown temperature"))
		self.AutoFanRefreshTimer.start(1000, True)
	
	def quit(self):
		cfg.save()
		config.usage.fan.save()
		AutoFan.startAutoFan()
		self.close()


class AutoFanMain():
	def __init__(self):
		self.AutoFanTimers = eTimer()
		self.AutoFanTimers.timeout.get().append(self.refreshTemp)
		self.AutoFanLogTimer = eTimer()
		self.AutoFanLogTimer.timeout.get().append(self.saveLog)

	def startAutoFan(self):
		if config.usage.fan.value == "auto":
			self.AutoFanTimers.start(10000, True) # wait 10s on start enigma2
		self.AutoFanLogTimer.start(5000, False)

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
		mode = self.getFanMode()
		if config.usage.fan.value == "on" and mode != "on":
			self.setFanMode("on")
		elif config.usage.fan.value == "off" and mode != "off":
			self.setFanMode("off")
		else: # mode = auto
			temperature = self.getTemperature()
			if temperature is not None:
				print("[AutoFan] temperature: %d\u00b0C" % temperature)
				if temperature > int(cfg.temperature.value):
					mode = "auto"
					self.setFanMode("auto")
				else:
					mode = "off"
				self.setFanMode(mode)
			else:
				print("[AutoFan] cannot read temperature")
			self.AutoFanTimers.start(int(cfg.refresh.value) * 1000, True)

	def header2Log(self):
		try:
			with open("/tmp/autofan.log", "w") as f:
				f.write("%s\n" % strftime("%Y.%m.%d %H:%M:%S"))
				f.write("-------------------\n")
		except Exception as e:
				print("[AutoFan] Failed to write header to log: %s" % e)

	def saveLog(self):
		if cfg.log.value:
			try:
				with open("/tmp/autofan.log", "a") as f:
					timestamp = strftime("%H:%M:%S")
					fan = 0 if self.getFanMode() == "off" else 1
					diff = self.getTemperature() - int(cfg.temperature.value)
					f.write("%s,%s,%d,%d,%s\n" % (timestamp, fan, int(cfg.temperature.value), self.getTemperature(), "{:+d}".format(diff)))
			except Exception as e:
				print("[AutoFan] Failed to write to log: %s" % e)

AutoFan = AutoFanMain()