# Meteo Viewer - Plugin E2
#
# by ims (c) 2011-2024
# 2024 remove FileList by jbleyel@OpenA.TV
# 2024 completely overworked (skins, downloads, configs, etc. by Mr.Servo@OpenA.TV)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#

from calendar import timegm
from glob import glob
from os import system, unlink
from os.path import join, isfile
from requests import get, exceptions
from time import gmtime, strftime, localtime, time, mktime, strptime, sleep

from enigma import ePicLoad, eTimer
from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigDirectory, ConfigSelection
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.HelpMenu import HelpableScreen
from Tools.Directories import fileExists, resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CONFIG
from twisted.internet.reactor import callInThread

from . import _  # for localized messages

VERSION = "v2.0"
TMPDIR = "/tmp/"
SUBDIR = "meteo"
PPATH = resolveFilename(SCOPE_CURRENT_PLUGIN, "MeteoViewer/pictures/")
E2PATH = resolveFilename(SCOPE_CONFIG)

# LIST OF USED NAMES IN MENU,OPTIONS AS INFO ("All" must be at last)
INA = ["North America"]
IAUSTRALIA = ["Australia", "Australia extended", "Australia IR"]
IANIMATED = ["Nederland - radar", "Germany - radar", "Great Britain - radar"]
IWO = [
	"Europe WO", "Great Britain WO", "France WO", "Iberia WO",
	"Italia WO", "Germany WO", "Scandinavia WO", "Ukraine/Romania WO",
	"Poland WO", "Near-East WO", "Russia WO", "Greece WO",
	"Iceland WO", "Canary Islands WO", "Baltic States WO", "Turkey WO"
	]
IWOi = [
	"Europe WO Infra", "Great Britain WO Infra", "France WO Infra", "Iberia WO Infra",
	"Italia WO Infra", "Germany WO Infra", "Scandinavia WO Infra", "Ukraine/Romania WO Infra",
	"Poland WO Infra", "Near-East WO Infra", "Russia WO Infra", "Greece WO Infra",
	"Iceland WO Infra", "Canary Islands WO Infra", "Baltic States WO Infra", "Turkey WO Infra"
	]
INFO = ["IR Central Europe", "VIS-IR Czech Republic", "IR BT Czech Republic", "24h-MF Czech Republic", "Czech Storm", "Czech Radar"]
INFO += IWO + IWOi + IANIMATED + IAUSTRALIA + INA + ["All"]

# LIST OF USED INDEX NAMES AS TYPES: ("all" must be at last")
NA = ["na"]
AUSTRALIA = ["aus", "ause", "ausi"]
ANIMATED = ["nla1", "dea", "uka"]
WO = ["im00", "im01", "im02", "im03", "im04", "im05", "im06", "im08", "im09", "im10", "im11", "im12", "im13", "im14", "im15", "im16"]
WOi = ["vm00", "vm01", "vm02", "vm03", "vm04", "vm05", "vm06", "vm08", "vm09", "vm10", "vm11", "vm12", "vm13", "vm14", "vm15", "vm16"]
TYPE = ["ir", "vis", "bt", "24m", "storm", "csr"]
TYPE += WO + WOi + ANIMATED + AUSTRALIA + NA + ["all"]

last_item = len(TYPE) + 1  # = max config.plugins.meteoviewer.type
# position of BACKGROUND and MER must be equal as position of SUBDIR and TYPE. For unused item use e.png
BACKGROUND = ["bg.png", "2bg.png", "2bg.png", "2bg.png", "e.png", "radar.png"]
for i in range(6, last_item):
	BACKGROUND.append("e.png")
MER = ["merce.png", "mercz.png", "mercz.png", "mercz.png", "estorm.png"]
for i in range(5, last_item):
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
for index, entry in enumerate(INFO):
	choicelist.append((index, entry))
config.plugins.meteoviewer.type = ConfigSelection(default="7", choices=choicelist)

# CHOICES FOR AFTER "ALL" (WITHOUT "ALL"):
config.plugins.meteoviewer.typeafterall = ConfigSelection(default="7", choices=config.plugins.meteoviewer.type.choices[:-1])
config.plugins.meteoviewer.display = ConfigSelection(default="3", choices=[("0", _("none")), ("1", _("info")), ("2", _("progress bar")), ("3", _("info and progress bar"))])
config.plugins.meteoviewer.localtime = ConfigYesNo(default=False)
config.plugins.meteoviewer.delete = ConfigSelection(default="4", choices=[("0", _("no")), ("1", _("current type")), ("2", _("all types")), ("3", _("older than max. interval")), ("4", _("older than downloaded interval"))])
config.plugins.meteoviewer.delend = ConfigYesNo(default=True)
config.plugins.meteoviewer.tmpdir = ConfigDirectory(TMPDIR)
config.plugins.meteoviewer.mer = ConfigYesNo(default=False)
choicelist = []
for i in range(16, 65):
	choicelist.append(("%d" % i, "%s mins" % i))
config.plugins.meteoviewer.wo_releaseframe_delay = ConfigSelection(default="47", choices=choicelist)
cfg = config.plugins.meteoviewer

TMPDIR = cfg.tmpdir.value


class meteoViewer(Screen, HelpableScreen):
	skin = """
		<screen name="meteoViewer" position="center,10" size="800,698" backgroundColor="#20000000" title="MeteoViewer" resolution="1280,720" flags="wfNoBorder" >
			<widget source="title" render="Label" position="0,0" size="495,40" font="Regular;30" halign="left" valign="bottom" />
			<widget name="border" position="0,70" zPosition="2" size="800,600" alphatest="on"/>
			<widget name="mer" position="0,70" zPosition="3" size="800,600" alphatest="on"/>
			<widget name="frames" position="0,70" zPosition="1" size="800,600" alphatest="on"/>
			<ePixmap position="40,36" size="160,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/red.png" zPosition="2" alphatest="blend" scaleFlags="keepAspect" />
			<ePixmap position="220,36" size="160,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/green.png" zPosition="2" alphatest="blend" scaleFlags="keepAspect" />
			<ePixmap position="400,36" size="160,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/yellow.png" zPosition="2" alphatest="blend" scaleFlags="keepAspect" />
			<ePixmap position="580,36" size="160,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/blue.png" zPosition="2" alphatest="blend" scaleFlags="keepAspect" />
			<widget source="key_red" render="Label" position="40,36" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget source="key_green" render="Label" position="220,36" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget source="key_yellow" render="Label" position="400,36" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<widget source="key_blue" render="Label" position="580,36" zPosition="3" size="160,30" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			<ePixmap position="391,70" size="18,10" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/top.png" zPosition="4" alphatest="on" scaleFlags="keepAspect" />
			<ePixmap position="0,361" size="10,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/left.png" zPosition="4" alphatest="on" scaleFlags="keepAspect" />
			<ePixmap position="790,361" size="10,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/right.png" zPosition="4" alphatest="on" scaleFlags="keepAspect" />
			<ePixmap position="391,660" size="18,10" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MeteoViewer/pictures/bottom.png" zPosition="4" alphatest="on" scaleFlags="keepAspect" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,676" zPosition="4" size="800,2" transparent="0" scaleFlags="keepAspect" />
			<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="720,678" size="14,14" zPosition="4" scaleFlags="keepAspect" />
			<widget font="Regular;18" halign="left" position="740,674" render="Label" size="60,20" source="global.CurrentTime" transparent="0" valign="center" zPosition="4" >
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget source="msg" render="Label" position="0,674" zPosition="4" size="745,24" valign="center" halign="left" font="Regular;18" transparent="0" foregroundColor="white" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,696" zPosition="4" size="800,2" transparent="0" scaleFlags="keepAspect" />
			<widget name="download" position="120,680" zPosition="5" borderWidth="1" size="100,12" backgroundColor="#0000ff" />
			<widget name="slide" position="450,680" zPosition="5" borderWidth="0" size="210,6" backgroundColor="dark" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.MAINMENU = ["Czech meteo", "Animated", "Weather Online", "Weather Online Infra", "Australia", "North America", _("All update")]
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
		self.mainMenuView = False
		self.queue = []
		self["title"] = StaticText()
		self["frames"] = Pixmap()
		self["border"] = Pixmap()
		self["mer"] = Pixmap()
		self["msg"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText(_("Download"))
		self["key_blue"] = StaticText(_("Options"))
		self["download"] = ProgressBar()
		self["download"].hide()
		self["slide"] = ProgressBar()
		self["slide"].hide()
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
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		self.borderLoad = ePicLoad()
		self.borderLoad.PictureData.get().append(self.showBorderPic)
		self.merLoad = ePicLoad()
		self.merLoad.PictureData.get().append(self.showMerPic)
		self.waitHTTPS = eTimer()
		self.waitHTTPS.timeout.get().append(self.httpsRun)
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
		return f"{TMPDIR}{SUBDIR}/{TYPE[num_typ]}/"

	def setWindowTitle(self):
		self["title"].setText(f"{_('MeteoViewer')} {VERSION}")

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
		self.mainMenuView = True
		for index, entry in enumerate(self.MAINMENU):
			menu.append((entry, str(index)))
		# "Download all" means big size. Do not show this item in menu, if tmpdir is placed in /tmp
		if not cfg.tmpdir.value.startswith('/tmp/'):
			menu.append((self.MAINMENU[len(self.MAINMENU) - 1], len(self.MAINMENU) - 1))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title=_("Select wanted meteo type:"), list=menu, selection=self.selection)

	def menuCallback(self, choice):
		if choice is None:
			self.end()
			return
		self.mainMenuView = False
		self.displayMeteoType()
		if choice[1] == len(self.MAINMENU) - 1:  # ALL
			self.typ = len(TYPE) - 1  # all
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
		if item == "0":  # CZ
			for i in range(0, 6):
				submenu.append((INFO[i], TYPE[i]))
		elif item == "1":  # ANIMATED
			for i in range(len(ANIMATED)):
				submenu.append((IANIMATED[i], ANIMATED[i]))
		elif item == "2":  # WEATHER ONLINE
			for i in range(0, len(WO)):
				submenu.append((IWO[i], WO[i]))
		elif item == "3":  # WEATHER ONLINE Infra
			for i in range(0, len(WOi)):
				submenu.append((IWOi[i], WOi[i]))
		elif item == "4":  # AUSTRALIA
			for i in range(0, len(AUSTRALIA)):
				submenu.append((IAUSTRALIA[i], AUSTRALIA[i]))
		elif item == "5":  # NA
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
		self["title"].setText(f"{_('MeteoViewer')} {VERSION} - {INFO[self.typ]}")

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
			print("[MeteoViewer] download - type: %s" % TYPE[self.typ])
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
			print("[MeteoViewer] NR: %d" % self.dlFrame)
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
		self.waiting = eTimer()
		self.waiting.timeout.get().append(self.waitingRefresh)
		self.waiting.start(100, True)

	def waitingRefresh(self):
		if self.dlFrame:
			self.waiting.start(100, True)
		else:
			self.isReading = False
			self.refreshLast = False
			self.statistic()
			self.readFiles(last_frame=False, green=False)
			self.slideShowTimer.start(int(cfg.time.value), True)

	def setRefreshFlag(self):
		self.refreshFlag = True
		self.refreshTimer.start(int(cfg.refresh.value) * 60000, True)

	def getFilesFromDir(self, directory, matchingPattern=""):
		result = []
		files = glob(f"{directory}*")
		files.sort()
		files = [x.split("/")[-1] for x in files]  # extract filename
		for file in files:
			path = join(directory, file)
			if not matchingPattern or matchingPattern == f".{file.split('.')[-1]}":
				result.append(file)
		return result

	def readFiles(self, last_frame=True, empty_frame=True, border=False, green=True, delay=0.2):
		self.setExtension()
		self.maxFrames = 0
		self.frame = []
		for file in self.getFilesFromDir(self.getDir(self.typ), self.EXT):
			self.frame.append(file[:-4])
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
		print("[MeteoViewer] >>> Files readed=%d, skipped=%d, time: %d:%02d min" % (self.x, self.errFrame, (self.endTime - self.beginTime) // 60, (self.endTime - self.beginTime) % 60))

	def setIndex(self):
		self.idx = self.startIdx = 0
		if TYPE[self.typ] == "storm":
			if self.maxFrames > int(cfg.nr.value) // 4 * 6 and cfg.frames.value == "0":
				self.startIdx = self.maxFrames - int(cfg.nr.value) // 4 * 6 - 1
		else:
			if self.maxFrames > int(cfg.nr.value) and cfg.frames.value == "0":
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
		path = f"{self.getDir(self.typ)}{self.frame[self.idx]}{self.EXT}"
		if fileExists(path):
			self.displayFrame(path)
			self.displayInfo(self.idx + 1, self.maxFrames, self.frame[self.idx])
			if cfg.display.value > "1":
				self["slide"].show()

	def setExtension(self):
		if TYPE[self.typ] in ("nla", "uka", "nla1", "ausv"):
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
		#print(self.typ, TYPE[self.typ])
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
			sleep(1.0)
			self.isShow = False

	def displaySynaptic(self):
		if self.isShow:
			self.stopSlideShow()
		if self.isReading:
			self.isReading = False
		else:  # if is not slideshow with STOP button:
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
		self.maxMap = 0
		self.map = []
		for x in self.getFilesFromDir(f"{TMPDIR}{SUBDIR}/", ".gif"):
			self.map.append(x[:-4])
			self.maxMap += 1

	def displaySynoptic(self, decrease=False):
		if self.maxMap > 0:
			if decrease:  # for return from config only
				self.midx -= 1
			self.isSynaptic = True
			path = f"{TMPDIR}{SUBDIR}/{self.map[self.midx]}.gif"
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
			localTime = timegm(utcTime)
			return f"{strftime('%d.%m.%Y %H:%M', localtime(localTime))} {_('LT')}"
		else:
			return f"{strftime('%d.%m.%Y %H:%M', localtime(epochTimeUTC))} {_('UTC')}"

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
			unlink("%s%s" % (self.getDir(self.typ), self.frame[self.idx] + self.EXT))
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
		name = strftime("%Y%m%d%H%M", lastUTCTime) + self.EXT
		for x in self.getFilesFromDir(self.getDir(TYPE.index(typ)), self.EXT):
			if x < name:
				unlink("%s%s" % (self.getDir(TYPE.index(typ)), x))

	def downloadFiles(self, typ):
		self.isReading = True
		self.x = self.dlFrame = self.errFrame = 0

		if cfg.delete.value == "1" or cfg.delete.value == "2":
			self.displayMsg(_("Erase files..."))
			if typ == "all" or cfg.delete.value == "2":
				system(f"rm -r {TMPDIR}{SUBDIR} >/dev/null 2>&1")
			else:
				system(f"rm {self.getDir(TYPE.index(typ))}*.* >/dev/null 2>&1")

		system(f"mkdir {TMPDIR}{SUBDIR} >/dev/null 2>&1")
		if typ == "all":
			for i in range(0, len(TYPE) - 1):
				system("mkdir %s >/dev/null 2>&1" % (self.getDir(i)))
		else:
			system("mkdir %s >/dev/null 2>&1" % (self.getDir(TYPE.index(typ))))
		self.beginTime = time()
		if not self.stopRead and not self.refreshLast:  # dont read if refresh
			self.downloadOnce(typ)
		if not self.stopRead:
			if typ in ("ir", "vis", "bt", "24m", "csr", "dea", "uka", "nla1", "all"):
				self.downloadMain(typ)
			if typ in ("storm", "all"):
				self.downloadStorm(typ)
			if AUSTRALIA.count(typ) or typ == "all":
				self.downloadHourly30(typ)
			if WO.count(typ) or typ == "all":
				self.downloadWO(WO, typ)
			if WOi.count(typ) or typ == "all":
				self.downloadWO(WOi, typ)
			if NA.count(typ) or typ == "all":
				self.download30(typ)
		if self.typ == len(TYPE) - 1:  # from ALL after start of plugin set typ "After All"
			self.typ = int(cfg.typeafterall.value)
		self.stopRead = False

	def downloadOnce(self, typ):  # only, when is choose "Download"
		#print("[MeteoViewer] >>>Once>>>", typ, TYPE.index(typ))
		system(f"rm {TMPDIR}{SUBDIR}/*.* >/dev/null 2>&1")
		pictures = {"evropa/T2m_stredomori.gif": "03T2m_stredomori.gif",
			 		"evropa/RH_stredomori.gif": "04RH_stredomori.gif",
			 		"svet/T2m_svet.gif": "05T2m_svet.gif",
			 		"svet/T2m_amerika.gif": "06T2m_amerika.gif",
			 		"svet/T2m_jvazaust.gif": "07T2m_jvazaust.gif",
			 		"svet/T2m_afrika.gif": "08T2m_afrika.gif",
			 		"evropa/T2m_evropa.gif": "02T2m_evropa.gif",
			 		"evropa/analyza.gif": "01synoptic.gif"
			 		}
		for picture in pictures:
			url = f"http://portal.chmi.cz/files/portal/docs/meteo/om/{picture}"
			picfile = pictures.get(picture)
			if picfile:
				path = f"{TMPDIR}{SUBDIR}/{picfile}"
				self.downloadFrame(url, path)

	def downloadFrame(self, url, path):
		if self.stopRead:
			self.dlFrame = 0
			return False
		if not isfile(path):
			if url.startswith('https'):
				self.increment()
				self.queue.append((url, path))
				if not self.waitHTTPS.isActive():
					self.waitHTTPS.start(500, True)
			else:
				self.increment()
				callInThread(self.downloadPage, url, path)
		return True

	def download(self):
		if len(self.queue):
			(url, path) = self.queue.pop(0)
			self.downloadHttpsPicture(url, path)

	def downloadHttpsPicture(self, url, path):
		response = get(url)
		if response.status_code == 200:
			with open(path, 'wb') as f:
				f.write(response.content)
				self.dlFrame -= 1
				if len(self.queue):
					self.waitHTTPS.start(20, True)
		else:
			print("[MeteoViewer] Error in module 'downloadHttpsPicture':", url, path)
			self.dlFrame -= 1
			self.errFrame += 1
			self.x -= 1
			if len(self.queue):
				self.waitHTTPS.start(20, True)

	def downloadPage(self, url, path):
		url = url.encode("ascii", "xmlcharrefreplace").decode().replace(" ", "%20").replace("\n", "")
		headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36", "Accept": "text/html"}
		try:
			response = get(url, headers=headers, timeout=(3.05, 6))
			response.raise_for_status()
			content = response.content
			if response.status_code == 200:
				with open(path, 'wb') as f:
					f.write(content)
			self.dlFrame -= 1
		except exceptions.RequestException as error:
			print("[MeteoViewer] Error in module 'downloadPage':", error)
			self.dlFrame -= 1
			self.errFrame += 1

	def increment(self):
		self.x += 1
		self.dlFrame += 1

	def httpsRun(self):
		self.download()
		if self.stopRead:
			self.waitHTTPS.stop()
			self.dlFrame = 0

	def downloadMain(self, typ):
		#print("[MeteoViewer] >>>Main>>>", typ, TYPE.index(typ))
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
		for i in range(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))  # utc
			frTime = strftime("%H%M", gmtime(i))  # utc
			urls = {"ir": f"http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgce-ir/msgce.ir.{frDate}.{frTime}.0.jpg",
		   			"vis": f"http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-vis-ir/msgcz.vis-ir.{frDate}.{frTime}.0.jpg",
		   			"bt": f"http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-BT/msgcz.BT.{frDate}.{frTime}.0.jpg",
		   			"24m": f"http://www.chmi.cz/files/portal/docs/meteo/sat/msg_hrit/img-msgcz-24M/msgcz.24M.{frDate}.{frTime}.0.jpg",
		   			"dea": f"https://www.weatheronline.co.uk/daten/radar/dwddg/{frDate[:-4]}/{frDate[4:-2]}/{frDate[6:]}/{frTime}.gif",
		   			"uka": f"https://www.weatheronline.co.uk/daten/radar/ukuk/{frDate[:-4]}/{frDate[4:-2]}/{frDate[6:]}/{frTime}.gif",
		   			"nla": f"https://www.weatheronline.co.uk/daten/radar/ddlnw/{frDate[:-4]}/{frDate[4:-2]}/{frDate[6:]}/{frTime}.gif",
		   			"csr": f"http://portal.chmi.cz/files/portal/docs/meteo/rad/data_tr_png_1km/pacz23.z_max3d.{frDate}.{frTime}.0.png"
		   			}
			for urltype in urls:
				if typ == urltype or typ == "all":
					url = urls.get(urltype)
					if urltype:
						path = f"{self.getDir(TYPE.index(urltype))}{frDate}{frTime}.jpg"
						if not self.downloadFrame(url, path):
							break

	def downloadStorm(self, typ):
		#print("[MeteoViewer] >>>Storm>>>", typ, TYPE.index(typ))
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
		for i in range(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))  # utc
			frTime = strftime("%H%M", gmtime(i))  # utc
			url = f"http://www.chmi.cz/files/portal/docs/meteo/blesk/data/pacz21.blesk.{frDate}.{frTime}.10_9.png"
			path = f"{self.getDir(TYPE.index("storm"))}{frDate}{frTime}.png"
			if not self.downloadFrame(url, path):
				break

	def download30(self, typ):  # for download each 1h but in xx.30
		#print("[MeteoViewer] >>>30>>>", typ, TYPE.index(typ))
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
				for i in country:
					self.deleteOldFiles(i, gmtime(startDel))
			else:
				self.deleteOldFiles(typ, gmtime(startDel))
		j = 0
		for i in range(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))  # utc
			frTime = strftime("%H%M", gmtime(i))  # utc
			if typ == "na" or typ == "all":
				url = f"https://www.ssec.wisc.edu/data/us_comp/image{j}.jpg"
				path = f"{self.getDir(TYPE.index("na"))}{frDate}{frTime}.jpg"
				if not self.downloadFrame(url, path):
					break
				j += 1

	def downloadHourly30(self, typ):  # for download each 1h but in xx.30
		#print("[MeteoViewer] >>>Hourly30>>>", typ, TYPE.index(typ))
		country = AUSTRALIA
		interval = int(cfg.nr.value) * 900
		step = 3600			# 1 hour
		now = int(time())		# LT
		nowH = (now // step) * step - 1800  # last hour - 30 min
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
		for i in range(start, stop, step):
			frDate = strftime("%Y%m%d", gmtime(i))  # utc
			frTime = strftime("%H%M", gmtime(i))  # utc
			if typ == "aus" or typ == "all":
				url = f"http://www.bom.gov.au/gms/IDE00135.radar.{frDate}{frTime}.jpg"
				path = f"{self.getDir(TYPE.index('aus'))}{frDate}{frTime}.jpg"
				if not self.downloadFrame(url, path):
					break
			if typ == "ause" or typ == "all":
				url = f"http://www.bom.gov.au/gms/IDE00135.{frDate}{frTime}.jpg"
				path = f"{self.getDir(TYPE.index('ause'))}{frDate}{frTime}.jpg"
				if not self.downloadFrame(url, path):
					break
			if typ == "ausi" or typ == "all":
				url = f"http://www.bom.gov.au/gms/IDE00005.{frDate}{frTime}.gif"
				path = f"{self.getDir(TYPE.index('ausi'))}{frDate}{frTime}.jpg"
				if not self.downloadFrame(url, path):
					break

	def downloadWO(self, country, typ):
		interval = int(cfg.nr.value) * 900
		step = 900			# 15 minut
		now = int(time())		# LT
		now15 = (now // step) * step 	# last multiple min - f.eg. in 14:10 it is 14:00  (= last x min)
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
		for i in range(start, stop, step):
			name = strftime("%Y%m%d%H%M", gmtime(i))  # utc
			if typ == "all":
				for j in country:
					url = f"https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/{j}/{name[:-8]}/{name[4:-6]}/{name[6:-4]}/{name[8:]}.jpg"
					path = f"{self.getDir(TYPE.index(j))}{name}.jpg"
					if not self.downloadFrame(url, path):
						break
			else:
				url = f"https://www.weatheronline.co.uk/cgi-bin/getpicture?/daten/sat/{typ}/{name[:-8]}/{name[4:-6]}/{name[6:-4]}/{name[8:]}.jpg"
				path = f"{self.getDir(TYPE.index(typ))}{name}.jpg"
				if not self.downloadFrame(url, path):
					break
			if self.stopRead:
				break

	def eraseAllDirectory(self):
		system(f"rm -r {TMPDIR}{SUBDIR} >/dev/null 2>&1")

	def end(self):
		if self.mainMenuView:
			if self.isReading:
				self.stopRead = True
				return
			if cfg.delend.value:
				self.eraseAllDirectory()
		self.close()


class meteoViewerCfg(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "meteoViewerConfig", plugin="Extensions/MeteoViewer", PluginLanguageDomain="MeteoViewer")
