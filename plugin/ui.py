#################################################################################
#
#    Plugin for Enigma2, control fan in edision osmega
#
#    Coded by ims (c)2025, version 1.0.5
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
import subprocess
import gzip
import shutil
import os

desktop = getDesktop(0)
Width = desktop.size().width()
Height = desktop.size().height()
fullHD = False
if Width > 1280:
	fullHD = True

config.plugins.autofan = ConfigSubsection()
config.plugins.autofan.temperature = ConfigSelection(default="50", choices=[(str(i), "%d\u00b0C" % i) for i in range(35, 70)])
config.plugins.autofan.refresh = ConfigSelection(default="10", choices=[(str(i), _("%d s") % i) for i in range(5, 125, 5)])
config.plugins.autofan.log = ConfigYesNo(default=False)
config.plugins.autofan.log_date = ConfigYesNo(default=False)
cfg = config.plugins.autofan

log_path = "/tmp/autofan.log"

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
		self.list.append((_("Log to file"), cfg.log, _("Log time, fan state, and temperatures to a file every 5 seconds in 'auto' mode (without value descriptions), otherwise every 60 seconds (with value descriptions). Turning the device off and on will overwrite the '%s' file.") % log_path))
		if cfg.log.value:
			self.list.append((4 * " " + _("Date in the log"), cfg.log_date, _("Add the date to the time entries in the log file.")))
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
			self.listMenu()
			if cfg.log.value:
				AutoFan.rotateLogBeforeEnable()
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
		self.AutoFanTimers.start(10000, True) # wait 10s on start enigma2
		self.saveLog()

	def getTemperature(self):
		try:
			with open("/proc/stb/fp/temp_sensor_avs", "r") as f:
				temp = f.read().strip()
				return int(temp)
		except Exception as e:
			print("[AutoFan] CPU temperature read error:", e)
			return -1

	def isDiskSleeping(self, dev="/dev/sda"):
		try:
			output = subprocess.check_output(["hdparm", "-C", dev], stderr=subprocess.DEVNULL, text=True)
			if "standby" in output.lower() or "sleeping" in output.lower():
				return True
			return False
		except Exception as e:
			print("[AutoFan] HDD sleep check error:", e)
			return False

	def getHDDTemperature(self, dev="/dev/sda"):
		try:
			output = subprocess.check_output(["smartctl", "-A", dev], stderr=subprocess.DEVNULL, text=True)
			for line in output.splitlines():
				if "Temperature_Celsius" in line or "Temperature_Internal" in line:
					parts = line.split()
					if len(parts) >= 10 and parts[-1].isdigit():
						return int(parts[-1])
		except Exception as e:
			print("[AutoFan] HDD temperature read error:", e)
			return -1

	def getFanMode(self):
		try:
			with open("/proc/stb/fp/fan", "r") as f:
				mode = f.read().strip()
				return mode
		except Exception as e:
			print("[AutoFan] Fan mode read error:", e)
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

	def rotateLogBeforeEnable(self):
		try:
			if os.path.exists(log_path):
				rotated_path = "/tmp/autofan_%s.log" % strftime("%Y%m%d-%H%M%S")
				os.rename(log_path, rotated_path)
				compressed_path = rotated_path + ".gz"
				with open(rotated_path, "rb") as f_in, gzip.open(compressed_path, "wb") as f_out:
					shutil.copyfileobj(f_in, f_out)
				try:
					os.remove(rotated_path)
				except:
					print("[AutoFan] cannot remove %d" % rotated_path)
				self.writeHeader()
		except Exception as e:
			print("[AutoFan] Failed to write header to log: %s" % e)

	def writeHeader(self):
		with open(log_path, "w") as f:
			f.write("%s\n" % strftime("Start %Y.%m.%d %H:%M:%S"))
			f.write(39 * "-" + "\n")

	def saveLog(self):
		if cfg.log.value:
			if not os.path.exists(log_path):
				self.writeHeader()
			try:
				with open(log_path, "a") as f:
					timestamp = strftime("%Y.%m.%d %H:%M:%S") if cfg.log_date.value else strftime("%H:%M:%S")
					fan = 0 if self.getFanMode() == "off" else 1
					hdd = ",sleep" if self.isDiskSleeping() else ""
					if config.usage.fan.value == "auto":
						diff = self.getTemperature() - int(cfg.temperature.value)
						f.write("%s,%s,%d,%d,%s,%d%s\n" % (timestamp, fan, int(cfg.temperature.value), self.getTemperature(), "{:+d}".format(diff), self.getHDDTemperature(), hdd))
					else:
						f.write("%s,fan:%s,cpu:%d,hdd:%d%s\n" % (timestamp, fan, self.getTemperature(), self.getHDDTemperature(), hdd))
			except Exception as e:
				print("[AutoFan] Failed to write to log: %s" % e)
		delay = 60000 if config.usage.fan.value != "auto" else 5000
		self.AutoFanLogTimer.start(delay, False)

AutoFan = AutoFanMain()
