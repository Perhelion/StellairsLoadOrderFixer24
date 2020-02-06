# -*- coding: utf-8 -*-
#!python3.6
#coding: utf8
import json
import os
import ctypes  # An included library with Python install.
import sys
import traceback
import platform
import zipfile

mods_registry =  "mods_registry.json"
enabledMods = {}
data = {}
# hashList = [] # the visible order (PDX launcher)
modList = [] # the modId order (game, which is in reverse to hashList)
bak_ext = '.bak' # backup file extension


class Mod():
	def __init__(self, hashKey, name, modId):
		self.hashKey = hashKey
		self.name = name
		self.modId = modId
		self.sortedKey = name.encode('ascii', errors='ignore')


def mBox(title, text, style):
	if platform.system() == 'Windows':
		return ctypes.windll.user32.MessageBoxW(0, text, title, style)
	else:
		print(title + ": " + text)

def abort(message):
	mBox('abort', message, 0)
	sys.exit(1)


def getModList(data):
	modList = []
	for key, data in data.items():
		modId = data.get('gameRegistryId') or data.get('steamId')
		name = data.get('displayName')
		if not modId or not name:
			print('key %s not found in %s' % (key, data))
		else:
			mod = Mod(key, name, modId)
			modList.append(mod)
	
	modList.sort(key=lambda m: m.sortedKey, reverse=True)
	return modList


def tweakModOrder(arr):
	for i in range(len(arr) - 1, 0, -1):
		j = i - 1
		if arr[j].sortedKey.startswith(arr[i].sortedKey):
			tmp = arr[j]
			arr[j] = arr[i]
			arr[i] = tmp

	if len(arr):
		return arr
	abort('no mod found')


def loadJsonOrder(file):
	"Read JSON files"
	file = os.path.join(settingPath, file)
	json_data = {}
	if os.path.isfile(file):
		# Remove old backup
		if os.path.isfile(file + bak_ext):
			print("Remove old backup file")
			os.remove(file + bak_ext)
		with open(file, 'r') as f:
			json_data = json.load(f)
			if len(json_data) < 1:
				print('Loading failed:', file)
	else:
		print('Please enable at least one mod', file)
	return (json_data, file)

def writeJsonOrder(data, file):
	"Write JSON file"
	# Backup
	os.rename(file, file + bak_ext)
	with open(file, 'w') as f:
		json.dump(data, f, indent=2)


def getHashFromName(name):
	for h, d in data.items():
		if d.get("displayName") == name:
			return h
	return False

def getIndexFromHash(h, name):
	i = [i for i, mod in enumerate(modList) if mod.hashKey == h]
	if len(i):
		return i[0]
	# if h and h in hashList:
	# 	return hashList.index(h)
	print(name, 'Hashkey not found in game_data.json', h)


def checkDependencies(descCnt, hashKey, name, order):
	if descCnt and len(descCnt) > 30 and "dependencies" in descCnt:
		d = False
		dependencies = []
		# print("Read dependencies in descriptor.mod file for", name)
		descCnt = descCnt.splitlines()
		for line in descCnt:
			if "dependencies" in line and not d:
				d = True
				if not "}" in line:
					continue
				else:
					print("dependencies oneliner?", line)
			if d:
				if not "}" in line:
					line = line.strip().strip('\"')
					dependencies.append(line)
				else:
					break

		# if gId not in enabledMods['enabled_mods']:
		# 	return print(name, 'is not enabled?')

		if len(dependencies):
			for n in dependencies:
				i = getHashFromName(n)
				if not i:
					print('Error dependencie: %s not found for %s in mods_registry' % (n.encode(), name))
					continue
				i = getIndexFromHash(i, name)
				if type(i) is int and i > order:
					print("FIX dependencie: %s - %d is lower than %d - %s" % (name, order, i, n))
					item = modList.pop(order)
					modList.insert(i, item) # insert before
					order = i
				# else:
				# 	print("dependencie error %s is not enabled for %s" % (n, name))

			# print(str(dependencies).encode())
		# 	return dependencies

def getModDescription(mod, order):
	# Extracting ZIP archives as recommended since 2.4
	d = data[mod.hashKey]
	dirPath = d.get("dirPath")
	archivePath = d.get("archivePath")
	descriptor = ''
	desc_file = os.path.join(dirPath, "descriptor.mod")
	displayName = mod.sortedKey

	if not dirPath or not os.path.isdir(dirPath):
		return

	if os.path.isfile(desc_file):
		with open(desc_file, encoding='UTF-8') as f:
			descriptor = f.read()

	if archivePath and not descriptor:
		if os.path.isfile(archivePath):
			try:
				with zipfile.ZipFile(archivePath, 'r') as zip_ref:
					zip_ref.extractall(dirPath)
				# del data_loaded[i]["archivePath"]
				zip_ref.close()
				print("Mod archive extraxcted %s" % displayName)
				# os.remove(archivePath)
			except Exception as e:
				print(errorMesssage(e))
				pass
		# else:
		# 	del data_loaded[i]["archivePath"]
		if os.path.isfile(desc_file):
			with open(desc_file, encoding='UTF-8') as f:
				descriptor = f.read()

	if descriptor:
		checkDependencies(descriptor, mod.hashKey, displayName, order)
	else:
		print("Error: no descriptor.mod for %s" % displayName)


def run():
	global mods_registry
	global modList
	global enabledMods
	global data
	# global hashList

	mods_registry = os.path.join(settingPath, mods_registry)
	enabledMods, dlc_load = loadJsonOrder('dlc_load.json')
	displayOrder, game_data = loadJsonOrder('game_data.json')

	# if 'modsOrder' in displayOrder:
	# 	hashList = displayOrder['modsOrder'] or hashList
	with open(mods_registry, encoding='UTF-8') as json_file:
		data = json.load(json_file)
		modList = getModList(data)
		# make sure UIOverhual+SpeedDial will load after UIOverhual
		modList = tweakModOrder(modList)
	
	idList = enabledMods['enabled_mods']
	# Sort after dependencies
	for i, mod in enumerate(modList):
		getModDescription(mod, i)

	displayOrder['modsOrder'] = [mod.hashKey for mod in modList] # hashList
	enabledMods['enabled_mods'] = [mod.modId for mod in reversed(modList) if mod.modId in idList]
	# print(*["%i: %s" % (i, mod.sortedKey.decode('ascii')) for i, mod in enumerate(modList)], sep = "\n")
	writeJsonOrder(enabledMods, dlc_load)
	writeJsonOrder(displayOrder, game_data)


def errorMesssage(error):
	error_class = e.__class__.__name__  # 取得錯誤類型
	detail = e.args[0]  # 取得詳細內容
	_, _, tb = sys.exc_info()  # 取得Call Stack
	lastCallStack = traceback.extract_tb(tb)[-1]  # 取得Call Stack的最後一筆資料
	fileName = lastCallStack[0]  # 取得發生的檔案名稱
	lineNum = lastCallStack[1]  # 取得發生的行號
	funcName = lastCallStack[2]  # 取得發生的函數名稱
	return "File \"{}\", line {}, in {}: [{}] {}".format(
		fileName, lineNum, funcName, error_class, detail)


def test():
	mod1 = Mod("", "!(", "")
	mod2 = Mod("", "!（更多中文", "")
	mod3 = Mod("", "UI + PD", "")
	mod4 = Mod("", "UI", "")
	mod5 = Mod("", "UI + Speed Dial", "")
	modList = [mod1, mod2, mod3, mod4, mod5]
	modList.sort(key=lambda m: m.sortedKey, reverse=True)
	print([x.sortedKey for x in modList])
	tweaked = tweakModOrder(modList)
	print([x.sortedKey for x in tweaked])


# try:
# 	# sys.setdefaultencoding() should NEVER be used
# 	reload(sys)  # Reload does the trick!
# 	sys.setdefaultencoding('UTF8')
# except:
# 	print('set encoding failed')

# check Stellaris settings location
locations = [
	".", "..",
	os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive',
				 'Stellaris'),
	os.path.join(os.path.expanduser('~'), '.local', 'share',
				 'Paradox Interactive', 'Stellaris')
]
settingPath = [s for s in locations if os.path.isfile(os.path.join(s, mods_registry))]

if len(settingPath) > 0:
	settingPath = settingPath[0] 
	print('Find Stellaris setting at ', settingPath)
	try:
		run()
		mBox('', 'done', 0)
	except Exception as e:
		print(errorMesssage(e))
		mBox('error', errorMesssage(e), 0)
else:
	mBox('error', 'unable to locate "%s"' % mods_registry, 0)
