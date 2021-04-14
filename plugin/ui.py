# for localized messages
from . import _
#
#  Meteo Viewer - Plugin E2
#
#  by ims (c) 2011-2020
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

import os
from enigma import ePicLoad, getDesktop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from enigma import eTimer
from Components.FileList import FileList
from Components.config import ConfigSubsection, ConfigYesNo, ConfigText, ConfigDirectory, ConfigSelection, getConfigListEntry, config
from Components.Label import Label
from Components.ConfigList import ConfigListScreen, ConfigList
from os import system
from time import gmtime, strftime, localtime, time, mktime, strptime, ctime
import calendar
import enigma
from Tools.Directories import fileExists
from Screens.ChoiceBox import ChoiceBox
from Components.ProgressBar import ProgressBar
import requests

TMPDIR = "/tmp/"
SUBDIR = "meteo"

# LIST OF USED NAMES IN MENU,OPTIONS AS INFO ("All" must be at last)
INA = ["North America"]
IAUSTRALIA = ["Australia", "Australia extended", "Australia IR"]
IANIMATED = ["Nederland - radar", "Germany - radar", "Great Britain - radar"]
IWO = [
	"Europe WO", "Great Britain WO", "France WO", "Iberia WO",
	"Italia WO", "Germany WO", "Scandinavia WO", "Ukraine/Romania WO",
	"Poland WO", "Near-East WO", "Russia WO", "Greece WO",
	"Iceland WO", "Canary Islands  WO", "Baltic States WO", "Turkey WO"
	]
IWOi = [
	"Europe WO Infra", "Great Britain WO Infra", "France WO Infra", "Iberia WO Infra",
	"Italia WO Infra", "Germany WO Infra", "Scandinavia WO Infra", "Ukraine/Romania WO Infra",
	"Poland WO Infra", "Near-East WO Infra", "Russia WO Infra", "Greece WO Infra",
	"Iceland WO Infra", "Canary Islands  WO Infra", "Baltic States WO Infra", "Turkey WO Infra"
	]

INFO = ["IR Central Europe", "VIS-IR Czech Republic", "IR BT Czech Republic", "24h-MF Czech Republic", "Czech Storm", "Czech Radar"]
INFO += IWO
INFO += IWOi
INFO += IANIMATED
INFO += IAUSTRALIA
INFO += INA
INFO += ["All"]

# LIST OF USED INDEX NAMES AS TYPES: ("all" must be at last")
NA = ["na"]
AUSTRALIA = ["aus", "ause", "ausi"]
ANIMATED = ["nla1", "dea", "uka"]
WO = [
	"im00", "im01", "im02", "im03",
	"im04", "im05", "im06", "im08",
	"im09", "im10", "im11", "im12",
	"im13", "im14", "im15", "im16"
	]
WOi = [
	"vm00", "vm01", "vm02", "vm03",
	"vm04", "vm05", "vm06", "vm08",
	"vm09", "vm10", "vm11", "vm12",
	"vm13", "vm14", "vm15", "vm16"
	]

TYPE = ["ir", "vis", "bt", "24m", "storm", "csr"]
TYPE += WO
TYPE += WOi
TYPE += ANIMATED
TYPE += AUSTRALIA
TYPE += NA
TYPE += ["all"]

PPATH = "/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/"
E2PATH = "/etc/enigma2/"

last_item = len(TYPE) # = max config.plugins.meteoviewer.type

HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True

# position of BACKGROUND and MER must be equal as position of SUBDIR and TYPE. For unused item use e.png
BACKGROUND = ["bg.png", "2bg.png", "2bg.png", "2bg.png", "e.png", "radar.png"]
for i in range(6, last_item + 1):
	BACKGROUND.append("e.png")
MER = ["merce.png", "mercz.png", "mercz.png", "mercz.png", "estorm.png"]
for i in range(5, last_item + 1):
	MER.append("e.png")
EMPTYFRAME = "e.jpg"

RADAR_MM = "radar_mm.png"

del last_item

config.plugins.meteoviewer = ConfigSubsection()
config.plugins.meteoviewer.nr = ConfigSelection(default="8", choices=[("4", "1h"), ("8", "2h"), ("12", "3h"), ("24", "6h"), ("48", "12h"), ("96", "24h"), ("192", "48h")])
config.plugins.meteoviewer.frames = ConfigSelection(default="0", choices=[("0", _("downloaded interval")), ("1", _("all frames"))])
config.plugins.meteoviewer.time = ConfigSelection(default="750", choices=[("400", "400 ms"), ("500", "500 ms"), ("600", "600 ms"), ("750", "750 ms"), ("1000", "1s"), ("2000", "2s"), ("5000", "5s"), ("10000", "10s")])
config.plugins.meteoviewer.refresh = ConfigSelection(default="0", choices=[("0", "no"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("10", "10"), ("15", "15")])
config.plugins.meteoviewer.slidetype = ConfigSelection(default="0", choices=[("0", _("begin")), ("1", _("actual position"))])
config.plugins.meteoviewer.download = ConfigYesNo(default=False)
# CHOICES FOR OPTIONS:
choicelist = []
for i in range(0, len(INFO)):
	choicelist.append(("%d" % i, "%s" % INFO[i]))
config.plugins.meteoviewer.type = ConfigSelection(default="7", choices=choicelist)

# CHOICES FOR AFTER "ALL" (WITHOUT "ALL"):
config.plugins.meteoviewer.typeafterall = ConfigSelection(default="7", choices=config.plugins.meteoviewer.type.choices[:-1])
config.plugins.meteoviewer.display = ConfigSelection(default="3", choices=[("0", _("none")), ("1", _("info")), ("2", _("progress bar")), ("3", _("info and progress bar"))])
config.plugins.meteoviewer.localtime = ConfigYesNo(default=False)
config.plugins.meteoviewer.delete = ConfigSelection(default="4", choices=[("0", _("no")), ("1", _("current type")), ("2", _("all types")),
										("3", _("older than max. interval")), ("4", _("older than downloaded interval"))])
config.plugins.meteoviewer.delend = ConfigYesNo(default=True)
config.plugins.meteoviewer.tmpdir = ConfigDirectory(TMPDIR)
config.plugins.meteoviewer.mer = ConfigYesNo(default=False)
choicelist = []
for i in range(16, 65):
	choicelist.append(("%d" % i, "%s mins" % i))
config.plugins.meteoviewer.wo_releaseframe_delay = ConfigSelection(default="47", choices=choicelist)
cfg = config.plugins.meteoviewer

TMPDIR = cfg.tmpdir.value

from twisted.internet.defer import DeferredSemaphore
from twisted.web.client import downloadPage


class LimitedDownloader:
	def __init__(self, howMany):
		self._semaphore = DeferredSemaphore(howMany)

	def downloadPage(self, *a, **kw):
		return self._semaphore.run(downloadPage, *a, **kw)


class meteoViewer(Screen, HelpableScreen):

	if HD:
		cx = "center"			# x-position of window 
		cy = "60"			# y-position of window
		sx = 800 			# x-size of window
		sy = 650			# y-size of window
		bgcolor = "#00000000"		# background of window
		# size for picture:
		px = 0				#
		py = 30
		pw = 800			# width of pictures
		ph = 600			# height of pictures
		# arrows:
		tx = 391			# top
		ty = py
		lx = 0				# left
		ly = 321
		rx = 790			# right
		ry = ly
		bx = tx				# bottom
		by = ph + py - 10
		# status bar, clock:
		msg_y = ph + py
		div_y = msg_y - 2		# top line of statusbar
		div_w = sx
		cli_x = sx - 55 - 15 - 10	# x-position of clock's icon
		cli_y = msg_y + 3
		cl_x = sx - 55			# x-position of clock
		cl_y = msg_y
		msg_w = cl_x			# width of status bar
		div2_y = msg_y + 20		# bottom line of statusbar
		down_x = 120
		down_y = msg_y + 5
		slide_x = 450
		slide_y = msg_y + 7
	else:
		cx = "center"
		cy = 50
		sx = 640
		sy = 500
		bgcolor = "#31000000"
		# size for picture:
		px = 20
		py = 30
		pw = 600			# width of pictures
		ph = 450			# height of pictures
		# arrows:
		tx = 311			# top
		ty = py
		lx = 0				# left
		ly = 250
		rx = 630			# right
		ry = ly
		bx = tx				# bottom
		by = ph + py - 10
		# status bar, clock:
		msg_y = ph + py + 2
		div_y = msg_y - 2		# top line of statusbar
		div_w = sx
		cli_x = sx - 55 - 15 - 10	# x-position of clock's icon
		cli_y = msg_y + 3
		cl_x = sx - 55			# x-position of clock
		cl_y = msg_y
		msg_w = cl_x			# width of status bar
		div2_y = msg_y + 20		# bottom line of statusbar
		down_x = 100
		down_y = msg_y + 4
		slide_x = 330
		slide_y = msg_y + 7

	skin = """
		<screen name="meteoViewer" position="%s,%s" size="%s,%s" backgroundColor="%s" title="MeteoViewer">

			<widget name="border" position="%s,%s" zPosition="2" size="%s,%s" alphatest="on"/>
			<widget name="mer" position="%s,%s" zPosition="3" size="%s,%s" alphatest="on"/>
			<widget name="frames" position="%s,%s" zPosition="1" size="%s,%s" alphatest="on"/>

			<ePixmap position="  0,0" size="160,30" pixmap="%s%s" zPosition="2" alphatest="blend" />
			<ePixmap position="160,0" size="160,30" pixmap="%s%s" zPosition="2" alphatest="blend" />
			<ePixmap position="320,0" size="160,30" pixmap="%s%s" zPosition="2" alphatest="blend" />
			<ePixmap position="480,0" size="160,30" pixmap="%s%s" zPosition="2" alphatest="blend" />

			<widget name="key_red"    position="  0,0" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget name="key_green"  position="160,0" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget name="key_yellow" position="320,0" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget name="key_blue"   position="480,0" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />

			<ePixmap position="%s,%s" size="18,10" pixmap="%s%s" zPosition="4" alphatest="on" />
			<ePixmap position="%s,%s" size="10,18" pixmap="%s%s" zPosition="4" alphatest="on" />
			<ePixmap position="%s,%s" size="10,18" pixmap="%s%s" zPosition="4" alphatest="on" />
			<ePixmap position="%s,%s" size="18,10" pixmap="%s%s" zPosition="4" alphatest="on" />

			<ePixmap pixmap="skin_default/div-h.png" position="0,%s" zPosition="4" size="%s,3" transparent="0" />
			<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="%s,%s" size="14,14" zPosition="4"/>
			<widget font="Regular;18" halign="left" position="%s,%s" render="Label" size="55,20" source="global.CurrentTime" transparent="0" valign="center" zPosition="4">
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget name="msg" position="0,%s" zPosition="4" size="%s,20" valign="center" halign="left" font="Regular;18" transparent="0" foregroundColor="white" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,%s" zPosition="4" size="%s,2" transparent="0" />

			<widget name="download" position="%s,%s" zPosition="5" borderWidth="1" size="100,12" backgroundColor="#0000ff" />
			<widget name="slide" position="%s,%s" zPosition="5" borderWidth="0" size="210,6" backgroundColor="dark" />

		</screen>""" % (cx, cy, sx, sy, bgcolor,
				px, py, pw, ph,
				px, py, pw, ph,
				px, py, pw, ph,
				PPATH, "red.png", PPATH, "green.png", PPATH, "yellow.png", PPATH, "blue.png",
				tx, ty, PPATH, "top.png",
				lx, ly, PPATH, "left.png",
				rx, ry, PPATH, "right.png",
				bx, by, PPATH, "bottom.png",
				div_y, div_w,
				cli_x, cli_y,
				cl_x, cl_y,
				msg_y, msg_w,
				div2_y, div_w,
				down_x, down_y, 
				slide_x, slide_y)

	def __init__(self, session):
		self.skin = meteoViewer.skin
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setup_title = _("MeteoViewer")

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.end, _("exit plugin")),
			"ok": (self.lastFrame, _("go to last frame")),
			})

		self["MeteoViewerActions"] = HelpableActionMap(self, "MeteoViewerActions",
			{
			"menu": (self.showMenu, _("menu")),
			"left": (self.previousFrame, _("go to previous frame")),
			"right": (self.nextFrame, _("go to next frame")),
			"up": (self.increase_typ, _("switch to next meteo type")),
			"down": (self.decrease_typ, _("switch to previous meteo type")),
			"red": (self.end, _("exit plugin")),
			"green": (self.slideButton, _("play/stop slideshow")),
			"play": (self.runSlideShow, _("play slideshow")),
			"yellow": (self.download_delayed, _("run/abort download")),
			"blue": (self.callCfg, _("options")),
			"stop": (self.stopSlideShow, _("stop slideshow/synaptic map")),
			"tv": (self.displaySynaptic, _("synaptic maps")),
			"8": (self.deleteFrame, _("delete current frame")),
			"previous": (self.firstFrame, _("go to first downloaded frame")),
			"next": (self.lastFrame, _("go to last downloaded frame")),
			#"1": (self.refreshFrames, _("refresh last frame")),
			}, -2)

		self.MAINMENU = ["Czech meteo", "Animated", "Weather Online", "Weather Online Infra", "Australia", "North America", "All update"]

		self["frames"] = Pixmap()
		self.picload = enigma.ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self["border"] = Pixmap()
		self.borderLoad = enigma.ePicLoad()
		self.borderLoad.PictureData.get().append(self.showBorderPic)

		self["mer"] = Pixmap()
		self.merLoad = enigma.ePicLoad()
		self.merLoad.PictureData.get().append(self.showMerPic)

		self["msg"] = Label()

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label()
		self["key_yellow"] = Label(_("Download"))
		self["key_blue"] = Label(_("Options"))

		self["download"] = ProgressBar()
		self["download"].hide()
		self["slide"] = ProgressBar()
		self["slide"].hide()

		self.x = 0
		self.dlFrame = 0
		self.errFrame = 0
		self.idx = 0
		self.EXT = ".jpg"
		self.startIdx = 0
		self.maxFrames = 0
		self.filesOK = False
		self.isShow = False
		self.typ = int(cfg.type.value)
		self.last_frame = False
		self.isReading = False
		self.stopRead = False
		self.isSynaptic = False
		self.beginTime = 0
		self.endTime = 0
		self.refreshLast = False
		self.refreshFlag = False
		self.midx = 0
		self.maxMap = 0
		self.selection = 0
		self.firstSynaptic = False
		self.mainMenu = False

		self.queue = []
		self.waitHTTPS = eTimer()
		self.waitHTTPS.timeout.get().append(self.httpsRun)

		self.Limited = LimitedDownloader(5) # limit for parallel downloading

		if cfg.download.value:
			self.onLayoutFinish.append(self.download_delayed)
		else:
			if self.typ == (len(TYPE) - 1):
				self.typ = int(cfg.typeafterall.value)
			self.onLayoutFinish.append(self.readFiles)
		self.onShown.append(self.setParams)

	def setParams(self):
		self.displayMeteoType()
		par = [self["frames"].instance.size().width(), self["frames"].instance.size().height(), 1, 1, False, 0, "#00000000"]
		self.picload.setPara(par)
		par = [self["border"].instance.size().width(), self["frames"].instance.size().height(), 1, 1, False, 0, "#00000000"]
		self.borderLoad.setPara(par)
		par = [self["mer"].instance.size().width(), self["frames"].instance.size().height(), 1, 1, False, 0, "#00000000"]
		self.merLoad.setPara(par)

	def showPic(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["frames"].instance.setPixmap(ptr.__deref__())
			self["frames"].show()

	def showBorderPic(self, picInfo=None):
		ptr = self.borderLoad.getData()
		if ptr != None:
			self["border"].instance.setPixmap(ptr.__deref__())
			self["border"].show()

	def showMerPic(self, picInfo=None):
		ptr = self.merLoad.getData()
		if ptr != None:
			self["mer"].instance.setPixmap(ptr.__deref__())
			self["mer"].show()

	def getDir(self, num_typ):
		return TMPDIR + SUBDIR + "/" + TYPE[num_typ] + "/"

	def setWindowTitle(self):
		self.setTitle(_("MeteoViewer"))

	def runSlideShow(self):
		if not self.isShow:
			self.slideShow()
	
	def slideButton(self):
		if self.isShow:
			self.stopSlideShow()
		else:
			self.slideShow()

	def showMenu(self):
		if self.isReading:
			return
		menu = []
		self.mainMenu = True
		j = 0
		for i in range(0, len(self.MAINMENU) - 1):
			menu.append((self.MAINMENU[i], "%d" % (j)))
			j += 1
		# "Download all" means big size. Do not show this item in menu, if tmpdir is placed in /tmp
		if not cfg.tmpdir.value.startswith('/tmp/'):
			menu.append((self.MAINMENU[len(self.MAINMENU) - 1], len(self.MAINMENU) - 1))

		self.session.openWithCallback(self.menuCallback, ChoiceBox, title=_("Select wanted meteo type:"), list=menu, selection=self.selection)

	def menuCallback(self, choice):
		if choice is None:
			self.end()
			return

		self.mainMenu = False
		self.displayMeteoType()
		if choice[1] == len(self.MAINMENU) - 1:	# ALL
			self.typ = len(TYPE) - 1 # all
			self.download_delayed()
# 		EXAMLPE FOR SINGLE ITEMs RUNNING FROM MAIN MENU:
#		elif choice[1] == "2":	# GLOBE
#			self.typ = int(TYPE.index("glb"))
#			self.readFiles()
#			if not self.filesOK:
#				self.download_delayed()
		else:
			self.selection = int(choice[1])
			self.subMenu(choice[1])

	def subMenu(self, item):
		#"Czech meteo", "Animated", "Weather Online", "Weather Online Infra", "Australia", "North America", "All update"
		submenu = []

		if item == "0":		# CZ
			for i in range(0, 6):
				submenu.append((INFO[i], TYPE[i]))
		elif item == "1":	# ANIMATED
			for i in range(len(ANIMATED)):
				submenu.append((IANIMATED[i], ANIMATED[i]))
		elif item == "2":	# WEATHER ONLINE
			for i in range(0, len(WO)):
				submenu.append((IWO[i], WO[i]))
		elif item == "3":	# WEATHER ONLINE Infra
			for i in range(0, len(WOi)):
				submenu.append((IWOi[i], WOi[i]))
		elif item == "4":	# AUSTRALIA
			for i in range(0, len(AUSTRALIA)):
				submenu.append((IAUSTRALIA[i], AUSTRALIA[i]))
		elif item == "5":	# NA
			for i in range(0, len(NA)):
				submenu.append((INA[i], NA[i]))
		self.session.openWithCallback(self.submenuCallback, ChoiceBox, title=_("Select destination:"), list=submenu)

	def submenuCallback(self, choice):
		if choice is None:
			self.showMenu()
			return

		self.selection = 0
		self.typ = int(TYPE.index(choice[1]))
		self.displayMeteoType()
		if self.typ == len(TYPE) - 1:
			self.download_delayed()
		else:
			self.readFiles(green=False)
			if not self.filesOK:
				self.download_delayed()

	def increase_typ(self):
		slide = False
		if self.isShow:
			self.stopSlideShow()
			slide = True
		if not self.isShow:
			if self.typ >= (len(TYPE) - 1 - 1):
				self.typ = 0
			else:
				self.typ += 1
		#self.setExtension()
		self.displayMeteoType()
		#self.redrawBorder()
		self.readFiles(delay=0.1, border=True)

		if slide:
			self.slideShow()

	def decrease_typ(self):
		slide = False
		if self.isShow:
			self.stopSlideShow()
			slide = True
		if not self.isShow:
			if self.typ <= 0:
				self.typ = len(TYPE) - 1 - 1
			else:
				self.typ -= 1
		#self.setExtension()
		self.displayMeteoType()
		#self.redrawBorder()
		self.readFiles(delay=0.1, border=True)

		if slide:
			self.slideShow()

	def displayMeteoType(self):
		self.setTitle(_("MeteoViewer") + " - " + INFO[self.typ])

	def displayMsg(self, message):
		self["msg"].setText("  " + message)

	def download_delayed(self):
		self["slide"].hide()
		if self.isReading:
			self.stopRead = True
		else:
			self.displayMsg(_("Prepare..."))
			self.waitGS = eTimer()
			self.waitGS.timeout.get().append(self.downloadFrames)
			self.waitGS.start(250, True)

	def downloadFrames(self):
		self.emptyFrame()
		if self.isShow:
			self.stopSlideShow()
		if not self.isShow:
#			if cfg.tmpdir.value.startswith('/tmp/'):
#				self.typ = int(cfg.typeafterall.value)

			self["key_red"].setText(_("Back"))
			self["key_green"].setText("")
			self["key_yellow"].setText(_("Abort"))
			self["key_blue"].setText("")

			print "[MeteoViewer] download - type: %s" % TYPE[self.typ]
			self.downloadFiles(TYPE[self.typ])

			self.displayMsg(_("Download:"))
			self["download"].setValue(0)
			self["download"].show()
			self.Wait = eTimer()
			self.Wait.timeout.get().append(self.waitingFiles)
			self.Wait.start(500, True)
		else:
			self.displayMsg(_("Stop slideshow, please!"))

	def waitingFiles(self):
		if self.dlFrame:
			print "[MeteoViewer] NR: %d" % self.dlFrame
			self["download"].setValue(int(100.0 * (self.x - self.dlFrame) / self.x + 0.25))
			self.Wait.start(100, True)
		else:
			self["download"].setValue(self.x)
			self["download"].hide()
			self.displayMsg("")
			self.isReading = False
			self.statistic()
			self["key_red"].setText(_("Back"))
			self["key_green"].setText(_("Slideshow"))
			self["key_yellow"].setText(_("Download"))
			self["key_blue"].setText(_("Options"))
			self.stopRead = False
			self.readFiles()
			self.readMap()

	def refreshFrames(self):
		self.refreshLast = True
		self.displayMsg(_("refresh..."))

		self.downloadFiles(TYPE[self.typ])

		self.wait = eTimer()
		self.wait.timeout.get().append(self.waitingRefresh)
		self.wait.start(100, True)

	def waitingRefresh(self):
		if self.dlFrame:
			self.wait.start(100, True)
		else:
			self.isReading = False
			self.refreshLast = False
			self.statistic()
			self.readFiles(last_frame=False, green=False)
			self.slideShowTimer.start(int(cfg.time.value), True)

	def setRefreshFlag(self):
		self.refreshFlag = True
		self.refreshTimer.start(int(cfg.refresh.value) * 60000, True)
		
	def readFiles(self, last_frame=True, empty_frame=True, border=False, green=True, delay=0.2):
		self.setExtension()
		filelist = FileList(self.getDir(self.typ), matchingPattern=self.EXT)

		self.maxFrames = 0
		self.frame = []
		for x in filelist.getFileList():
			if (x[0][1] != True):
				self.frame.append(x[0][0][:-4])
				self.maxFrames += 1
		self.filesOK = False
		if self.maxFrames != 0:
			self.filesOK = True
			self.setIndex()
			if green:
				self["key_green"].setText(_("Slideshow"))
			if last_frame:
				self.waitLF = eTimer()
				self.waitLF.timeout.get().append(self.lastFrame)
				self.waitLF.start(int(delay) * 100, True)
		else:
			self.setIndex()
			if empty_frame:
				self.emptyFrame()
			if border:
				self.redrawBorder()
			self["slide"].hide()
			self.displayMsg(_("No files found!"))

	def statistic(self):
		self.endTime = time()
		print "[MeteoViewer] >>> Files readed=%d, skipped=%d, time: %d:%02d min" % (self.x, self.errFrame, (self.endTime - self.beginTime) // 60, (self.endTime - self.beginTime) % 60)

	def setIndex(self):
		self.idx = self.startIdx = 0
		if TYPE[self.typ] == "storm":
			if self.maxFrames > int(cfg.nr.value) / 4 * 6:
				if cfg.frames.value == "0":
					self.startIdx = self.maxFrames - int(cfg.nr.value) / 4 * 6 - 1
		else:
			if self.maxFrames > int(cfg.nr.value):
				if cfg.frames.value == "0":
					self.startIdx = self.maxFrames - int(cfg.nr.value)
		self.idx = self.startIdx

	def afterCfg(self, data=True):
		if self.isSynaptic:
			self.displaySynoptic(True)
			self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
			if cfg.display.value > "1":
				self["slide"].show()
			return

		self.displayMeteoType()
		if self.lastdir != cfg.tmpdir.value:
			self.readFiles(delay=0.5)
			if self.filesOK:
				self.redrawBorder()
		else:
			if self.last_frames != cfg.frames.value:
				self.readFiles()
			else:
				if self.filesOK:
					self.redrawFrame()
					self.redrawBorder()
		if not self.filesOK:
			self.displayMsg(_("Download pictures, please!"))

	def callCfg(self):
		if not self.isShow and not self.isReading:
			self.displayMsg("")
			self.emptyFrame()
			self["slide"].hide()
			self.lastdir = cfg.tmpdir.value
			self.last_typ = self.typ
			self.last_frames = cfg.frames.value
			self.session.openWithCallback(self.afterCfg, meteoViewerCfg)

	def redrawFrame(self):
		path = self.getDir(self.typ) + self.frame[self.idx] + self.EXT
		if fileExists(path):
			self.displayFrame(path)
			self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
			if cfg.display.value > "1":
				self["slide"].show()

	def setExtension(self):
		if TYPE[self.typ] in ("nla", "dea", "uka", "nla1", "ausi", "ausv"):
			self.EXT = ".gif"
		elif TYPE[self.typ] in ("storm", "csr"):
			self.EXT = ".png"
		else:
			self.EXT = ".jpg"

	def displayFrame(self, path):
		if TYPE[self.typ] == "csr":
			self.borderLoad.startDecode(path)
		else:
			self.picload.startDecode(path)

	def firstFrame(self):
		if self.isSynaptic:
			self.isSynaptic = False
		self.displayMeteoType()
		self.displayMsg("")
		if self.filesOK:
			self.redrawBorder()
			if not self.isShow:
				path = self.getDir(self.typ) + self.frame[self.startIdx] + self.EXT
				if fileExists(path):
					self.displayFrame(path)
					if cfg.display.value > "1":
						self["slide"].setValue(100)
						self["slide"].show()
						self.displayInfo(self.startIdx + 1, self.maxFrames, self.frame[self.idx])
					self.idx = self.startIdx
		else:
			self.emptyFrame()
			self.displayMsg(_("Download pictures, please!"))

	def lastFrame(self):
		#print self.typ, TYPE[self.typ]
		if self.isSynaptic:
			self.isSynaptic = False

		self.displayMeteoType()
		self.displayMsg("")
		if self.filesOK:
			self.redrawBorder()
			if not self.isShow:
				path = self.getDir(self.typ) + self.frame[self.maxFrames - 1] + self.EXT
				if fileExists(path):
					self.displayFrame(path)
					if cfg.display.value > "1":
						self["slide"].setValue(100)
						self["slide"].show()
						self.displayInfo(self.maxFrames, self.maxFrames, self.frame[self.maxFrames - 1])
					self.idx = self.maxFrames - 1
		else:
			self.emptyFrame()
			self.displayMsg(_("Download pictures, please!"))

	def nextFrame(self):
		if self.isSynaptic:
			self.isSynaptic = False
			self.redrawBorder()
		self.displayMsg("")
		if self.filesOK:
			if not self.isShow:
				if self.idx < (self.maxFrames - 1):
					self.idx += 1
				else:
					self.idx = self.startIdx
				path = self.getDir(self.typ) + self.frame[self.idx] + self.EXT
				if fileExists(path):
					self.displayFrame(path)
					self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
			else:
				self.displayMsg(_("Stop slideshow, please!"))
		else:
			self.displayMsg(_("No files found!"))

	def previousFrame(self):
		if self.isSynaptic:
			self.isSynaptic = False
			self.redrawBorder()
		self.displayMsg("")
		if self.filesOK:
			if not self.isShow:
				if self.idx > self.startIdx:
					self.idx -= 1
				else:
					self.idx = self.maxFrames - 1
				path = self.getDir(self.typ) + self.frame[self.idx] + self.EXT
				if fileExists(path):
					self.displayFrame(path)
					self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
			else:
				self.displayMsg(_("Stop slideshow, please!"))
		else:
			self.displayMsg(_("No files found!"))

	def redrawBorder(self):
		if self.isSynaptic:
			if TYPE[self.typ] != "csr":
				self.borderLoad.startDecode(PPATH + MER[len(TYPE) - 1])
			else:
				self.picload.startDecode(PPATH + BACKGROUND[len(BACKGROUND) - 1])
			self.merLoad.startDecode(PPATH + MER[len(TYPE) - 1])
			self.firstSynaptic = False
		else:
			if TYPE[self.typ] == "csr":
				self.picload.startDecode(PPATH + BACKGROUND[self.typ])
				if cfg.mer.value and fileExists(E2PATH + RADAR_MM):
					self.merLoad.startDecode(E2PATH + RADAR_MM)
				else:
					self.merLoad.startDecode(PPATH + RADAR_MM)
			else:
				self.borderLoad.startDecode(PPATH + BACKGROUND[self.typ])
				if cfg.mer.value:
					if TYPE[self.typ] in ("ir", "vis", "bt", "24m", "storm") and fileExists(E2PATH + MER[self.typ]):
						self.merLoad.startDecode(E2PATH + MER[self.typ])
					else:
						self.merLoad.startDecode(PPATH + MER[self.typ])
				else:
					self.merLoad.startDecode(PPATH + MER[len(TYPE) - 1])

	def slideShow(self):
		self.isSynaptic = False
		self.redrawBorder()
		self.slideShowTimer = eTimer()
		self.slideShowTimer.timeout.get().append(self.slideShowEvent)
		if int(cfg.refresh.value) > 0:
			self.refreshFlag = False
			self.refreshTimer = eTimer()
			self.refreshTimer.timeout.get().append(self.setRefreshFlag)
			self.refreshTimer.start(int(cfg.refresh.value) * 60000, True)
		if self.filesOK:
			self.isShow = True

			if cfg.slidetype == "0": 		# from begin
				self.idx = self.startIdx
			elif cfg.slidetype == "1":		# from actual position
				if self.idx > self.startIdx:
					self.idx += 1
					if self.idx >= self.maxFrames:
						self.idx = self.startIdx

			self["key_green"].setText(_("Stop Show"))
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self.slideShowTimer.start(500, True)

	def stopSlideShow(self):
		if self.isShow:
			self.slideShowTimer.stop()
			if int(cfg.refresh.value) > 0:
				self.refreshTimer.stop()
			self["key_green"].setText(_("Slideshow"))
			self["key_yellow"].setText(_("Download"))
			self["key_blue"].setText(_("Options"))
			if self.filesOK:
				if self.idx == self.startIdx:
					self.idx = self.maxFrames - 1
				else:
					self.idx -= 1
			else:
				self.emptyFrame()
				self.displayMsg(_("No files found!"))
			import time
			time.sleep(1.0)
			self.isShow = False

	def displaySynaptic(self):
		if self.isShow:
			self.stopSlideShow()
		if self.isReading:
			self.isReading = False
		else:	# if is not slideshow with STOP button:
			if not self.isSynaptic:
				self.firstSynaptic = True
			self.isSynaptic = True
			if self.firstSynaptic:
				self.redrawBorder()
			self.displaySynoptic()

	def slideShowEvent(self):
		if self.filesOK:
			if self.isShow:
				if self.idx < self.maxFrames:
					path = self.getDir(self.typ) + self.frame[self.idx] + self.EXT
					if fileExists(path):
						self.displayFrame(path)
						self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
						self.idx += 1
					self.slideShowTimer.start(int(cfg.time.value), True)
				else:   # pozastaveni na konci. Jestlize nechci, tak sloucit a jen zmenit podminku a index 
					if self.refreshFlag:
						self.refreshFrames()
						self.refreshFlag = False
					else:
						self.slideShowTimer.start(int(cfg.time.value), True)
					self.idx = self.startIdx
				#self.slideShowTimer.start(int(cfg.time.value), True)
		else:
			self.emptyFrame()
			self.displayMsg(_("No files found!"))

	def displayInfo(self, i, n, name):
		if cfg.display.value == "1":
			self.displayMsg(_("%s of %s  -  %s") % (i, n, self.timeFormat(name)))
		elif cfg.display.value == "2":
			self["slide"].setValue(int(100.0 * i / n + 0.25))
		elif cfg.display.value == "3":
			self.displayMsg(_("%s of %s  -  %s") % (i, n, self.timeFormat(name)))
			self["slide"].setValue(int(100.0 * i / n + 0.25))

	def readMap(self):
		filelist = FileList(TMPDIR + SUBDIR, matchingPattern=".gif")

		self.maxMap = 0
		self.map = []
		for x in filelist.getFileList():
			if (x[0][1] != True):
				self.map.append(x[0][0][:-4])
				self.maxMap += 1
			
	def displaySynoptic(self, decrease=False):
		if self.maxMap > 0:
			if decrease: # for return from config only
				self.midx -= 1
			self.isSynaptic = True			
			path = TMPDIR + SUBDIR + "/" + self.map[self.midx] + ".gif"
			if fileExists(path):
				self.displayFrame(path)
				#self.displayInfo(self.midx+1,self.maxMap,self.frame[self.midx])
			if self.midx < (self.maxMap - 1):
				self.midx += 1
			else:
				self.midx = 0

	def timeFormat(self, name):
		epochTimeUTC = mktime(strptime(name, '%Y%m%d%H%M'))
		if cfg.localtime.value:
			utcTime = localtime(epochTimeUTC)
			localTime = calendar.timegm(utcTime)
			return strftime("%d.%m.%Y %H:%M", localtime(localTime)) + " " + _("LT")
		else:
			return strftime("%d.%m.%Y %H:%M", localtime(epochTimeUTC)) + " " + _("UTC")

	def emptyFrame(self):
		if fileExists(PPATH + EMPTYFRAME):
			self.displayFrame(PPATH + EMPTYFRAME)

	def deleteFrame(self):
		if not self.isShow and not self.isReading:
			if self.filesOK:
				self.session.openWithCallback(self.eraseFrame, MessageBox, _("Are You sure delete this frame?"), MessageBox.TYPE_YESNO, default=False)
			else:
				self.displayMsg(_("No files found!"))

	def eraseFrame(self, answer):
		if answer is True:
			removedIdx = self.idx
			os.unlink("%s%s" % (self.getDir(self.typ), self.frame[self.idx] + self.EXT))
			self.readFiles(last_frame=False)
			if removedIdx > self.maxFrames - 1:
				self.idx = self.maxFrames - 1
			elif removedIdx < self.startIdx:
				self.idx = self.startIdx
			else:
				self.idx = removedIdx
			self.redrawFrame()
		else:
			return

	def deleteOldFiles(self, typ, lastUTCTime):
		self.setExtension()
		oldlist = FileList(self.getDir(TYPE.index(typ)), matchingPattern=self.EXT)
		name = strftime("%Y%m%d%H%M", lastUTCTime) + self.EXT
		for x in oldlist.getFileList():
			if (x[0][1] != True):
				if x[0][0] < name:
					os.unlink("%s%s" % (self.getDir(TYPE.index(typ)), x[0][0]))

	def downloadFiles(self, typ):
		self.isReading = True
		self.x = self.dlFrame = self.errFrame = 0

		if cfg.delete.value == "1" or cfg.delete.value == "2":
			self.displayMsg(_("Erase files..."))
			if typ == "all" or cfg.delete.value == "2":
				os.system("rm -r %s >/dev/null 2>&1" % (TMPDIR + SUBDIR))
			else:
				os.system("rm %s*.* >/dev/null 2>&1" % (self.getDir(TYPE.index(typ))))

		os.system("mkdir %s >/dev/null 2>&1" % (TMPDIR + SUBDIR))
		if typ == "all":
			for i in range(0, len(TYPE) - 1):
				os.system("mkdir %s >/dev/null 2>&1" % (self.getDir(i)))
		else:
			os.system("mkdir %s >/dev/null 2>&1" % (self.getDir(TYPE.index(typ))))

		self.beginTime = time()
		if not self.stopRead:
			if not self.refreshLast: # dont read if refresh
				self.downloadOnce(typ)

		if typ in ("ir", "vis", "bt", "24m", "csr", "dea", "uka", "nla1", "all"):
			if not self.stopRead:
				self.downloadMain(typ)
		if typ in ("storm", "all"):
			if not self.stopRead:
				self.downloadStorm(typ)
		if AUSTRALIA.count(typ) or typ == "all":
			if not self.stopRead:
				self.downloadHourly30(typ)
		if WO.count(typ) or typ == "all":
			if not self.stopRead:
				self.downloadWO(typ)
		if WOi.count(typ) or typ == "all":
			if not self.stopRead:
				self.downloadWOi(typ)
		if NA.count(typ) or typ == "all":
			if not self.stopRead:
				self.download30(typ)
		if self.typ == len(TYPE) - 1: # from ALL after start of plugin set typ "After All"
			self.typ = int(cfg.typeafterall.value)

		self.stopRead = False

	def downloadFail(self, failure):
		print "[MeteoViewer]", failure
		self.dlFrame -= 1
		self.errFrame += 1

	def afterDownload(self, result=None):
		self.dlFrame -= 1

	def increment(self):
		self.x += 1
		self.dlFrame += 1

	def downloadOnce(self, typ): # only, when is choose "Download"
		#print "[MeteoViewer] >>>Once>>>", typ,  TYPE.index(typ)
		os.system("rm %s/*.* >/dev/null 2>&1" % (TMPDIR + SUBDIR))

		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/evropa/T2m_stredomori.gif"
		path = "%s03T2m_stredomori.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/evropa/RH_stredomori.gif"
		path = "%s04RH_stredomori.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/svet/T2m_svet.gif"
		path = "%s05T2m_svet.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/svet/T2m_amerika.gif"
		path = "%s06T2m_amerika.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/svet/T2m_jvazaust.gif"
		path = "%s07T2m_jvazaust.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/svet/T2m_afrika.gif"
		path = "%s08T2m_afrika.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/evropa/T2m_evropa.gif"
		path = "%s02T2m_evropa.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)
		url = "http://portal.chmi.cz/files/portal/docs/meteo/om/evropa/analyza.gif"
		path = "%s01synoptic.gif" % (TMPDIR + SUBDIR + "/")
		self.downloadFrame(url, path)

	def downloadFrame(self, url, path):
		if self.stopRead:
			self.dlFrame = 0
			return False
		if not os.path.isfile(path):
			if url.startswith('https'):
				self.increment()
				self.queue.append((url, path))
				if not self.waitHTTPS.isActive():
					self.waitHTTPS.start(500, True)
			else:
				self.increment()
				self.Limited.downloadPage(url, path).addCallbacks(self.afterDownload).addErrback(self.downloadFail)
		return True

	def download(self):
		if len(self.queue):
			(url, path) = self.queue.pop(0)
			self.downloadHttpsPicture(url, path)

	def httpsRun(self):
		self.download()
		if self.stopRead:
			self.waitHTTPS.stop()
			self.dlFrame = 0
			return

	def downloadHttpsPicture(self, url, path):
		res = requests.get(url)
		if res.status_code == 200:
			with open(path, 'wb') as f:
				f.write(res.content)
				self.dlFrame -= 1
				if len(self.queue):
					self.waitHTTPS.start(20, True)
		else:
			print "[MeteoViewer] download failed for:", url, path
			self.dlFrame -= 1
			self.errFrame += 1
			self.x -= 1
			if len(self.queue):
				self.waitHTTPS.start(20, True)

	def downloadMain(self, typ):
		#print "[MeteoViewer] >>>Main>>>", typ,  TYPE.index(typ)
		interval = int(cfg.nr.value) * 900
		step = 900			# 15 minut
		now = int(time())		# LT
		now15 = (now // step) * step 	# last x min

		start = now15 - interval
		stop = now15 + step

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = now15 - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900
			if typ == "all":
				for i in ("ir", "vis", "bt", "24m", "csr", "dea", "uka", "nla1"):
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))	#utc
			frTime = strftime("%H%M", gmtime(i))	#utc
			if typ == "ir" or typ == "all":
				url = "http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgce-ir/msgce.ir.%s.%s.0.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("ir")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

			if typ == "vis" or typ == "all":
				url = "http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-vis-ir/msgcz.vis-ir.%s.%s.0.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("vis")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

			if typ == "bt" or typ == "all":
				url = "http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-BT/msgcz.BT.%s.%s.0.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("bt")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
				
			if typ == "24m" or typ == "all":
				url = "http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-24M/msgcz.24M.%s.%s.0.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("24m")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

			if typ == "dea" or typ == "all":
				url = "https://www.weatheronline.co.uk/daten/radar/dwddg/%s/%s/%s/%s.gif" % (frDate[:-4], frDate[4:-2], frDate[6:], frTime)
				path = "%s%s%s.gif" % (self.getDir(TYPE.index("dea")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
			if typ == "uka" or typ == "all":
				url = "https://www.weatheronline.co.uk/daten/radar/ukuk/%s/%s/%s/%s.gif" % (frDate[:-4], frDate[4:-2], frDate[6:], frTime)
				path = "%s%s%s.gif" % (self.getDir(TYPE.index("uka")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
			if typ == "nla1" or typ == "all":
				url = "https://www.weatheronline.co.uk/daten/radar/ddlnw/%s/%s/%s/%s.gif" % (frDate[:-4], frDate[4:-2], frDate[6:], frTime)
				path = "%s%s%s.gif" % (self.getDir(TYPE.index("nla1")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

			if typ == "csr" or typ == "all":
				url = "http://portal.chmi.cz/files/portal/docs/meteo/rad/data_tr_png_1km/pacz23.z_max3d.%s.%s.0.png" % (frDate, frTime)
				#url = "http://www.chmi.cz/files/portal/docs/meteo/rad/data/%s%s.gif" % (frDate[2:], frTime)
				path = "%s%s%s.png" % (self.getDir(TYPE.index("csr")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

	def downloadStorm(self, typ):
		#print "[MeteoViewer] >>>Storm>>>", typ, TYPE.index(typ)
		interval = int(cfg.nr.value) * 900
		step = 600			# 10 minut
		now = int(time())		# LT
		now10 = (now // step) * step 	# last x min
		start = now10 - interval
		stop = now10 + step

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = now10 - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900
			if typ == "all":
				for i in ("storm",):
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))	#utc
			frTime = strftime("%H%M", gmtime(i))	#utc
			url = "http://www.chmi.cz/files/portal/docs/meteo/blesk/data/pacz21.blesk.%s.%s.10_9.png" % (frDate, frTime)
			path = "%s%s%s.png" % (self.getDir(TYPE.index("storm")), frDate, frTime)
			if not self.downloadFrame(url, path):
				break

	def downloadHourly(self, typ): # for download each 1h - !!! IS NOT USED IN THIS TIME !!!
		#print "[MeteoViewer] >>>Hourly>>>", typ,  TYPE.index(typ)
		country = WE
		interval = int(cfg.nr.value) * 900
		step = 3600			# 1 hour
		now = int(time())		# LT
		nowH = (now // step) * step 	# last x min
		start = nowH - interval
		stop = nowH + step

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = nowH - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900
			if typ == "all":
				for i in country:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			name = strftime("%Y%m%d%H%M", gmtime(i)) #utc
			if typ == "we" or typ == "all":
				url = "http://www.metoffice.gov.uk/weather/images/eurir_sat_%s.jpg" % (name)
				path = "%s%s.jpg" % (self.getDir(TYPE.index("we")), name)
				if not self.downloadFrame(url, path):
					break
			if typ == "wevis" or typ == "all":
				url = "http://www.metoffice.gov.uk/weather/images/eurvis_sat_%s.jpg" % (name)
				path = "%s%s.jpg" % (self.getDir(TYPE.index("wevis")), name)
				if not self.downloadFrame(url, path):
					break

			if typ == "uk" or typ == "all":
				url = "http://www.metoffice.gov.uk/weather/images/ukir_sat_%s.jpg" % (name)
				path = "%s%s.jpg" % (self.getDir(TYPE.index("uk")), name)
				if not self.downloadFrame(url, path):
					break

			if typ == "ukvis" or typ == "all":
				url = "http://www.metoffice.gov.uk/weather/images/ukvis_sat_%s.jpg" % (name)
				path = "%s%s.jpg" % (self.getDir(TYPE.index("ukvis")), name)
				if not self.downloadFrame(url, path):
					break

	def download30(self, typ): # for download each 1h but in xx.30
		#print "[MeteoViewer] >>>30>>>", typ,  TYPE.index(typ)
		country = NA
		interval = 4 * 3600
		step = 1800			# 1 hour
		now = int(time())		# LT
		nowH = (now // step) * step
		start = nowH - interval
		stop = nowH + step

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = nowH - 4 * 3600
			if typ == "all":
				for i in NA:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))
		j = 0
		for i in xrange(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))	#utc
			frTime = strftime("%H%M", gmtime(i))	#utc
			if typ == "na" or typ == "all":
				url = "https://www.ssec.wisc.edu/data/us_comp/image%s.jpg" % (j)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("na")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
				j += 1

	def downloadHourly30(self, typ): # for download each 1h but in xx.30
		#print "[MeteoViewer] >>>Hourly30>>>", typ,  TYPE.index(typ)
		country = AUSTRALIA
		interval = int(cfg.nr.value) * 900
		step = 3600			# 1 hour
		now = int(time())		# LT
		nowH = (now // step) * step - 1800	# last hour - 30 min
		start = nowH - interval
		stop = nowH + step

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = nowH - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900 - 1800
			if typ == "all":
				for i in country:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))	#utc
			frTime = strftime("%H%M", gmtime(i))	#utc
			if typ == "aus" or typ == "all":
				url = "http://www.bom.gov.au/gms/IDE00135.radar.%s%s.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("aus")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
			if typ == "ause" or typ == "all":
				url = "http://www.bom.gov.au/gms/IDE00135.%s%s.jpg" % (frDate, frTime)
				path = "%s%s%s.jpg" % (self.getDir(TYPE.index("ause")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break
			if typ == "ausi" or typ == "all":
				url = "http://www.bom.gov.au/gms/IDE00005.%s%s.gif" % (frDate, frTime)
				path = "%s%s%s.gif" % (self.getDir(TYPE.index("ausi")), frDate, frTime)
				if not self.downloadFrame(url, path):
					break

	def downloadWO(self, typ):
		#print "[MeteoViewer] >>>WO>>", typ,  TYPE.index(typ)
		country = WO
		interval = int(cfg.nr.value) * 900
		step = 900			# 15 minut
		now = int(time())		# LT
		now15 = (now // step) * step 	# last multiple min - f.eg. in 14:10 it is 14:00
		start = now15 - interval
		rest = (now % step)		# f.eg. 14:10 - 14:00 = 10 minuts
		stop = now15 - int(cfg.wo_releaseframe_delay.value) * 60 + rest

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = now15 - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900
			if typ == "all":
				for i in country:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			name = strftime("%Y%m%d%H%M", gmtime(i)) #utc
			if typ == "all":
				for j in country:
					url = "https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/%s/%s/%s/%s/%s.jpg" % (j, name[:-8], name[4:-6], name[6:-4], name[8:])
					path = "%s%s.jpg" % (self.getDir(TYPE.index(j)), name)
					if not self.downloadFrame(url, path):
						break
			else:
				url = "https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/%s/%s/%s/%s/%s.jpg" % (typ, name[:-8], name[4:-6], name[6:-4], name[8:])
				path = "%s%s.jpg" % (self.getDir(TYPE.index(typ)), name)
				if not self.downloadFrame(url, path):
					break
			if self.stopRead:
				break

	def downloadWOi(self, typ):
		#print "[MeteoViewer] >>>WOi>>", typ,  TYPE.index(typ)
		country = WOi
		interval = int(cfg.nr.value) * 900
		step = 900			# 15 minut
		now = int(time())		# LT
		now15 = (now // step) * step 	# last x min
		start = now15 - interval
		rest = (now % step)
		stop = now15 - int(cfg.wo_releaseframe_delay.value) * 60 + rest

		if cfg.delete.value == "3" or cfg.delete.value == "4":
			startDel = start
			if cfg.delete.value == "3":
				startDel = now15 - int(cfg.nr.choices[len(cfg.nr.choices) - 1]) * 900
			if typ == "all":
				for i in country:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))

		for i in xrange(start, stop, step):
			name = strftime("%Y%m%d%H%M", gmtime(i)) #utc
			if typ == "all":
				for j in country:
					url = "https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/%s/%s/%s/%s/%s.jpg" % (j, name[:-8], name[4:-6], name[6:-4], name[8:])
					path = "%s%s.jpg" % (self.getDir(TYPE.index(j)), name)
					if not self.downloadFrame(url, path):
						break
			else:
				url = "https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/%s/%s/%s/%s/%s.jpg" % (typ, name[:-8], name[4:-6], name[6:-4], name[8:])
				path = "%s%s.jpg" % (self.getDir(TYPE.index(typ)), name)
				if not self.downloadFrame(url, path):
					break
			if self.stopRead:
				break

	def eraseAllDirectory(self):
		os.system("rm -r %s >/dev/null 2>&1" % (TMPDIR + SUBDIR))

	def end(self):
		if self.mainMenu:
			if self.isReading:
				self.stopRead = True
				return
			if cfg.delend.value:
				self.eraseAllDirectory()
				#cfg.delend.value = False
			self.close()
		else:
			self.showMenu()


class meteoViewerCfg(Screen, ConfigListScreen):

	bgcolor = "#31000000"
	if HD:
		bgcolor = "#00000000"

	skin = """
	<screen name="meteoViewerCfg" position="center,center" size="560,380" title="MeteoViewer Setup" backgroundColor="%s" >

		<ePixmap name="red"    position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap name="green"  position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />

		<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" /> 
		<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />

		<widget name="config" position="10,40" size="540,300" zPosition="1" transparent="0" backgroundColor="%s" scrollbarMode="showOnDemand" />

		<ePixmap pixmap="skin_default/div-h.png" position="0,355" zPosition="1" size="560,2" />
		<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="480,361" size="14,14" zPosition="3"/>
		<widget font="Regular;18" halign="right" position="495,358" render="Label" size="55,20" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">
			<convert type="ClockToText">Default</convert>
		</widget>

		<widget name="statusbar" position="10,359" size="460,20" font="Regular;18" backgroundColor="%s" />

	</screen>""" % (bgcolor, bgcolor, bgcolor)

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skin = meteoViewerCfg.skin
		self.setup_title = _("MeteoViewer Setup")
		self.version = "ims (c) 2012-2020 v1.78"

		self["key_green"] = Label(_("Save"))
		self["key_red"] = Label(_("Cancel"))
		self["statusbar"] = Label(self.version)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.save,
			"ok": self.ok,
			"red": self.exit,
			"cancel": self.exit
		}, -2)

		self.tmpdir_entry = getConfigListEntry(_("Directory for download"), cfg.tmpdir)

		meteoViewerCfglist = []
		meteoViewerCfglist.append(getConfigListEntry(_("Downloaded interval"), cfg.nr))
		meteoViewerCfglist.append(getConfigListEntry(_("Display"), cfg.frames))
		meteoViewerCfglist.append(getConfigListEntry(_("Slideshow's step"), cfg.time))
		meteoViewerCfglist.append(getConfigListEntry(_("Refresh slideshow"), cfg.refresh))
		meteoViewerCfglist.append(getConfigListEntry(_("Slideshow begins from"), cfg.slidetype))
		meteoViewerCfglist.append(getConfigListEntry(_("Download info on plugin's start"), cfg.download))
		meteoViewerCfglist.append(getConfigListEntry(_("Type of meteo info on start"), cfg.type))
		meteoViewerCfglist.append(getConfigListEntry(_("After download \"All\" switch to"), cfg.typeafterall))
		meteoViewerCfglist.append(getConfigListEntry(_("Delete old files before download"), cfg.delete))
		meteoViewerCfglist.append(getConfigListEntry(_("On exit delete files"), cfg.delend))
		meteoViewerCfglist.append(getConfigListEntry(_("Frames info"), cfg.display))
		meteoViewerCfglist.append(getConfigListEntry(_("Local time in info"), cfg.localtime))
		meteoViewerCfglist.append(getConfigListEntry(_("Parallels and meridians"), cfg.mer))
		meteoViewerCfglist.append(getConfigListEntry(_("Delay frame release for weatheronline"), cfg.wo_releaseframe_delay))

		meteoViewerCfglist.append(self.tmpdir_entry)
		ConfigListScreen.__init__(self, meteoViewerCfglist, session, on_change=self.changedEntry)

		self.onChangedEntry = []
		self.old_dir = cfg.tmpdir.value
		self.onShown.append(self.setWindowTitle)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self["statusbar"].setText(self.version)

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
	###

	def setWindowTitle(self):
		self.setTitle(_("MeteoViewer Setup"))

	def ok(self):
		from Screens.LocationBox import LocationBox
		from Components.UsageConfig import preferredPath
		currentry = self["config"].getCurrent()
		if currentry == self.tmpdir_entry:
			txt = _("Location for MeteoViewer")
			inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr"]
			self.session.openWithCallback(self.dirSelected, LocationBox, text=txt, currDir=cfg.tmpdir.value,
							bookmarks=config.movielist.videodirs, autoAdd=False, editDir=True,
							inhibitDirs=inhibitDirs, minFree=400) # in MB

	def dirSelected(self, res):
		if res is not None:
			cfg.tmpdir.value = res
		else:
			cfg.tmpdir.value = self.old_dir
		self["statusbar"].setText(self.version)

	def save(self):
		global TMPDIR
		if TMPDIR != cfg.tmpdir.value:
			os.system("rm -r %s >/dev/null 2>&1" % (TMPDIR + SUBDIR))
		TMPDIR = cfg.tmpdir.value
		if INFO[int(cfg.type.value)] == 'All' and cfg.tmpdir.value.startswith('/tmp/'):
			text = _("!!! '%s' as 'All' cannot be used with '/tmp/' !!!") % _("Type of meteo info on start")
			self["statusbar"].setText(text)
			return
		self.keySave()

	def exit(self):
		cfg.tmpdir.value = self.old_dir
		self.keyCancel()
