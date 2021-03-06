#-*- coding: utf-8 -*-
#!python3.6
#https://github.com/haifengkao/StellairsLoadOrderFixer24
import json
import os
import ctypes  # An included library with Python install.
import sys
import traceback
import platform
import zipfile

mods_registry =  'mods_registry.json'
idList = []
data = {}    # mods_registry.json
allTags = {}
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
	print(name, 'Hashkey not found in game_data.json', h)


def sortAfterTags(allTags, modList):
	"Merge allTags with modList"
	output  = []
	addAfter = []

	def _rmvDupes(dupes):
		"Keep last occurrence (prior higher indexes)"
		# list(dict.fromkeys(dupes))
		finalList = []
		for i in range(len(dupes)):
			d = dupes.pop()
			if d not in finalList:
				finalList.append(d)
		finalList.reverse()
		return finalList

	def _reorder_modList(name):
		nonlocal modList
		# name = name.decode()
		for mod in modList:
			if mod.sortedKey == name:
				modList.remove(mod)
				modList.append(mod)
				break

	def _insertPairTo_modList(name, name2):
		nonlocal modList
		# name = name.decode()
		comp = ''
		for i, mod in enumerate(modList):
			if mod.sortedKey == name2:
				comp = modList.pop(i)
				break
		if comp:
			for i, mod in enumerate(modList):
				if mod.sortedKey == name:
					modList.insert(i + 1, comp)
					break

	#prepend list
	for o in ('OST', 'Music', 'Sound', 'Graphics'):
		if o in allTags:
			output.extend(allTags.pop(o))
	#append list
	for o in ('AI', 'Utilities', 'Fixes'):
		if o in allTags:
			addAfter.extend(allTags.pop(o))
	#merge list
	for o in ('Patch'):
		if o in allTags:
			[x for x in allTags.pop(o) if x not in addAfter and (addAfter.append(x) or True)]

	# allTags = { t:l for t, l in allTags.items() }
	# print(type(addAfter),len(addAfter),*addAfter, sep="\n")

	for d in allTags:
		if len(d) == 1:
			# allTags.remove(t)
			continue
		if len(d) == 2:
			# allTags.remove(t)
			_insertPairTo_modList(d[0], d[1])
			continue
		output.extend(d)

	output.extend(addAfter)
	output = _rmvDupes(output)

	for name in output:
		_reorder_modList(name)

	return modList

def sortAfterDependencies(modList, dependencies, order, name):
	# print(order, name, dependencies)
	for n in dependencies:
		i = getHashFromName(n)
		if not i:
			if modList[order].modId in idList:
				print('Fail dependencie: %s not found for %s in mods_registry' % (n.encode(), name))
			continue
		i = getIndexFromHash(i, name)
		if type(i) is int and i > order:
			print("FIX dependencie: %s - %d is lower than %d - %s" % (name, order, i, n))
			item = modList.pop(order)
			modList.insert(i, item) # insert before
			order = i
	return modList


def sortDependencies(modList):
	for mod in modList:
		order = modList.index(mod) # Because changes on run
		if hasattr(mod, 'dependencies'):
			modList = sortAfterDependencies(modList, mod.dependencies, order, mod.sortedKey)
			# else:
			# 	print("dependencie error %s is not enabled for %s" % (n, name))
	return modList

# <tuple> descContent
def checkDependencies(descContent, order, name):
	global modList
	for descCnt in descContent:
		if descCnt and len(descCnt) > 30 and "dependencies" in descCnt:
			d = False
			dependencies = []
			descCnt = descCnt.splitlines()
			for line in descCnt:
				if "dependencies" in line and not d:
					d = True
					if not "}" in line:
						continue
					# else: print("dependencies oneliner?", line, name)
				if d:
					if not "}" in line:
						line = line.strip().strip('\"')
						dependencies.append(line)
					else:
						break
			# if gId not in enabledMods['enabled_mods']:
			# 	return print(name, 'is not enabled?')
			# Save only for later usage
			if len(dependencies):
				# print("Read dependencies in descriptor.mod file for", name, dependencies)
				modList[order].dependencies = dependencies
				# modList = sortAfterDependencies(modList, dependencies, order, name)

# <tuple> descContent
def checkTags(descContent, order, name):
	global allTags
	for descCnt in descContent:
		if descCnt and len(descCnt) > 30 and "tags" in descCnt:
			tags = []
			d = False
			# print("Read tags in descriptor.mod file for", name)
			descCnt = descCnt.splitlines()
			for line in descCnt:
				if "tags=" in line and not d:
					d = True
					if not "}" in line:
						continue
					# else: print("tags oneliner?", line, name)
				if d:
					if not "}" in line:
						line = line.strip().strip('\"')
						tags.append(line)
					else:
						break

			if len(tags):
				for t in tags:
					li = allTags.get(t, list())
					if name not in li:
						li.append(name) #.decode()
						allTags[t] = li


def specialOrder(modList):
	"Individual custom order (if no dependencie present)"
	specialNames = ("UI Overhaul Dynamic", "Dark UI", "Dark U1")
	specialList = []
	for specialName in specialNames:
		for i, mod in enumerate(modList):
			if specialName in mod.name:
				specialList.append((i, mod))

	if len(specialList) > 1:
		c, _ =  specialList.pop(0)
		for cmpMod in specialList:
			ix, cmpMod = cmpMod
			# print(c, ix, cmpMod.sortedKey)
			if c > ix:
				for i, mod in enumerate(modList):
					if mod.name == cmpMod.name:
						cmpMod = modList.pop(i)
						print("Special order", cmpMod.sortedKey, "after", modList[c-1].sortedKey)
						modList.insert(c, cmpMod)
						c += 1
						break
			else: c = ix

	return modList


def getModDescription():
	global allTags
	for order, mod in enumerate(modList):
		# Extracting ZIP archives as recommended since 2.4
		d = data[mod.hashKey]
		dirPath = d.get("dirPath")
		archivePath = d.get("archivePath")
		descriptor = []
		if not dirPath or not os.path.isdir(dirPath):
			print("Error: no dirPath found for %s in mods_registry" % mod.sortedKey)
			continue
		desc_file = os.path.join(dirPath, "descriptor.mod")
		displayName = mod.sortedKey
		gId = d.get("gameRegistryId")

		if desc_file and os.path.isfile(desc_file):
			with open(desc_file, encoding='UTF-8') as f:
				descriptor.append(f.read())

		if archivePath and not len(descriptor) and os.path.isfile(archivePath):
			try:
				with zipfile.ZipFile(archivePath, 'r') as zip_ref:
					zip_ref.extractall(dirPath)
				# del data_loaded[i]["archivePath"]
				zip_ref.close()
				print("Mod archive extraxcted for %s" % displayName)
				# os.remove(archivePath)
			except Exception as e:
				print(errorMesssage(e))
				pass
			# else:
			# 	del data_loaded[i]["archivePath"]
			if desc_file and os.path.isfile(desc_file):
				with open(desc_file, encoding='UTF-8') as f:
					descriptor.append(f.read())

		if not len(descriptor):
			print("Error: no descriptor.mod for %s" % displayName)

		# Read mod file
		desc_file = os.path.join(settingPath, 'mod', mod.modId.replace("mod/",""))
		if desc_file and os.path.isfile(desc_file):
			with open(desc_file, encoding='UTF-8') as f:
				descriptor.append(f.read())
		else:
			print("Error: no %s for %s" % (mod.modId, displayName))

		if len(descriptor):
			checkTags(descriptor, order, displayName)
			checkDependencies(descriptor, order, displayName)


def run():
	global mods_registry
	global modList
	global data
	global allTags
	global idList

	enabledMods = {}
	mods_registry = os.path.join(settingPath, mods_registry)
	enabledMods, dlc_load = loadJsonOrder('dlc_load.json')
	displayOrder, game_data = loadJsonOrder('game_data.json')

	with open(mods_registry, encoding='UTF-8') as f:
		data = json.load(f)
		modList = getModList(data)
	# make sure UIOverhual+SpeedDial will load after UIOverhual
	modList = tweakModOrder(modList)
	idList = enabledMods['enabled_mods']
	getModDescription()
	# print(*allTags, sep = "\n")
	# print(json.dumps({ t:[i.decode() for i in l] for t, l in allTags.items() if len(l) > 1 }, indent = 2))
	modList = sortAfterTags(allTags, modList)
	modList = specialOrder(modList)
	modList = sortDependencies(modList)

	displayOrder['modsOrder'] = [mod.hashKey for mod in modList] # hashList (for PDX launcher)
	enabledMods['enabled_mods'] = [mod.modId for mod in reversed(modList) if mod.modId in idList]
	writeJsonOrder(enabledMods, dlc_load)
	writeJsonOrder(displayOrder, game_data)
	print(*["%i: %s" % (i, mod.sortedKey.decode('ascii')) for i, mod in enumerate(modList)], sep = "\n")


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


# Check Stellaris settings location
settingPath = (".", "..",
	os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive', 'Stellaris'),
	os.path.join(os.path.expanduser('~'), '.local', 'share', 'Paradox Interactive', 'Stellaris'))
settingPath = [s for s in settingPath if os.path.isfile(os.path.join(s, mods_registry))]

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
