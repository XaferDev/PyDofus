#!/usr/bin/python3
# -*- coding: utf-8 -*-

import zlib, tempfile, io
from ._binarystream import _BinaryStream
from collections import OrderedDict

class InvalidDLMFile(Exception):
    def __init__(self, message):
        super(InvalidDLMFile, self).__init__(message)
        self.message = message

class DLM:
    def __init__(self, stream, key=None):
        if key == None:
            raise InvalidDLMFile("Map decryption key is empty.")

        self._stream = stream
        self._key = key

    def read(self):
        dlm_uncompressed = tempfile.TemporaryFile()
        dlm_uncompressed.write(zlib.decompress(self._stream.read()))
        dlm_uncompressed.seek(0)

        DLM_file_binary = _BinaryStream(dlm_uncompressed, True)

        map = Map(DLM_file_binary, self._key)
        map.read()

        dlm_uncompressed.close()

        return map.getObj()

    def write(self, obj):
        buffer = tempfile.TemporaryFile()
        buffer_stream = _BinaryStream(buffer, True)

        map = Map(buffer_stream, self._key)
        map.setObj(obj)
        map.write()

        buffer.seek(0)

        self._stream.write(zlib.compress(buffer.read()))

        buffer.close()

class Map:
    def __init__(self, raw, key):
        self._raw = raw
        self._key = key
        self._obj = OrderedDict()

        self.topArrowCell = []
        self.bottomArrowCell = []
        self.leftArrowCell = []
        self.rightArrowCell = []

    def raw(self):
        return self._raw

    def read(self):
        self._obj["header"] = self.raw().read_char()
        self._obj["mapVersion"] = self.raw().read_char()
        self._obj["mapId"] = self.raw().read_uint32()

        if self._obj["mapVersion"] >= 7:
            self._obj["encrypted"] = self.raw().read_bool()
            self._obj["encryptionVersion"] = self.raw().read_char()
            self.dataLen = self.raw().read_int32()

            if self._obj["encrypted"]:
                self.encryptedData = self.raw().read_bytes(self.dataLen)
                decryptedData = bytearray()
                for i in range(0, self.dataLen):
                    decryptedData.append(self.encryptedData[i] ^ ord(self._key[i % len(self._key)][0]))

                cleanData = io.BytesIO(decryptedData)
                self._raw = _BinaryStream(cleanData, True)

        self._obj["relativeId"] = self.raw().read_uint32()
        self._obj["mapType"] = self.raw().read_char()
        self._obj["subareaId"] = self.raw().read_int32()
        self._obj["topNeighbourId"] = self.raw().read_int32()
        self._obj["bottomNeighbourId"] = self.raw().read_int32()
        self._obj["leftNeighbourId"] = self.raw().read_int32()
        self._obj["rightNeighbourId"] = self.raw().read_int32()
        self._obj["shadowBonusOnEntities"]  = self.raw().read_int32()

        if self._obj["mapVersion"] >= 3:
            self._obj["backgroundRed"] = self.raw().read_char()
            self._obj["backgroundGreen"] = self.raw().read_char()
            self._obj["backgroundBlue"] = self.raw().read_char()
            self._obj["backgroundColor"] = (self._obj["backgroundRed"] & 255) << 16 | (self._obj["backgroundGreen"] & 255) << 8 | self._obj["backgroundBlue"] & 255

        if self._obj["mapVersion"] >= 4:
            self._obj["zoomScale"] = self.raw().read_uint16()
            self._obj["zoomOffsetX"] = self.raw().read_int16()
            self._obj["zoomOffsetY"] = self.raw().read_int16()

        self._obj["useLowPassFilter"] = self.raw().read_bool()
        self._obj["useReverb"] = self.raw().read_bool()

        if self._obj["useReverb"]:
            self._obj["presetId"] = self.raw().read_int32()
        else:
            self._obj["presetId"] = -1

        self._obj["backgroundsCount"] = self.raw().read_char()
        self._obj["backgroundFixtures"] = []
        for i in range(0, self._obj["backgroundsCount"]):
            bg = Fixture(self)
            bg.read()
            self._obj["backgroundFixtures"].append(bg.getObj())

        self._obj["foregroundsCount"] = self.raw().read_char()
        self._obj["foregroundsFixtures"] = []
        for i in range(0, self._obj["foregroundsCount"]):
            fg = Fixture(self)
            fg.read()
            self._obj["foregroundsFixtures"].append(fg.getObj())

        self._obj["unknown_1"] = self.raw().read_int32()
        self._obj["groundCRC"] = self.raw().read_int32()
        self._obj["layersCount"] = self.raw().read_char()

        self._obj["layers"] = []
        for i in range(0, self._obj["layersCount"]):
            la = Layer(self, self._obj["mapVersion"])
            la.read()
            self._obj["layers"].append(la.getObj())

        self._obj["cellsCount"] = 560 # MAP_CELLS_COUNT
        self._obj["cells"] = []
        for i in range(0, self._obj["cellsCount"]):
            cd = CellData(self, i, self._obj["mapVersion"])
            cd.read()
            self._obj["cells"].append(cd.getObj())

    def write(self):
        output_stream = self._raw
        cleanData = io.BytesIO() #tempfile.TemporaryFile()
        self._raw = _BinaryStream(cleanData, True)

        self.raw().write_uint32(self._obj["relativeId"])
        self.raw().write_char(self._obj["mapType"])
        self.raw().write_int32(self._obj["subareaId"])
        self.raw().write_int32(self._obj["topNeighbourId"])
        self.raw().write_int32(self._obj["bottomNeighbourId"])
        self.raw().write_int32(self._obj["leftNeighbourId"])
        self.raw().write_int32(self._obj["rightNeighbourId"])
        self.raw().write_int32(self._obj["shadowBonusOnEntities"])

        if self._obj["mapVersion"] >= 3:
            self.raw().write_char(self._obj["backgroundRed"])
            self.raw().write_char(self._obj["backgroundGreen"])
            self.raw().write_char(self._obj["backgroundBlue"])

        if self._obj["mapVersion"] >= 4:
            self.raw().write_int16(self._obj["zoomScale"])
            self.raw().write_int16(self._obj["zoomOffsetX"])
            self.raw().write_int16(self._obj["zoomOffsetY"])

        self.raw().write_bool(self._obj["useLowPassFilter"])
        self.raw().write_bool(self._obj["useReverb"])

        if self._obj["useReverb"]:
            self.raw().write_int32(self._obj["presetId"])

        self.raw().write_char(self._obj["backgroundsCount"])
        for i in range(0, self._obj["backgroundsCount"]):
            self._obj["backgroundFixtures"][i].write()

        self.raw().write_char(self._obj["foregroundsCount"])
        for i in range(0, self._obj["foregroundsCount"]):
            self._obj["foregroundsFixtures"][i].write()

        self.raw().write_int32(self._obj["unknown_1"])
        self.raw().write_int32(self._obj["groundCRC"])

        self.raw().write_char(self._obj["layersCount"])
        for i in range(0, self._obj["layersCount"]):
            self._obj["layers"][i].write()

        for i in range(0, self._obj["cellsCount"]):
            self._obj["cells"][i].write()

        input_stram = self._raw
        self._raw = output_stream
        cleanData.seek(0)

        self.raw().write_char(self._obj["header"])
        self.raw().write_char(self._obj["mapVersion"])
        self.raw().write_int32(self._obj["mapId"])

        if self._obj["mapVersion"] >= 7:
            self.raw().write_bool(self._obj["encrypted"])
            self.raw().write_char(self._obj["encryptionVersion"])
            self.raw().write_int32(len(cleanData.getbuffer())) # TODO: check len with getBuffer
            encryptedData = input_stram.read_bytes()
            for i in range(0, len(cleanData.getbuffer())):
                self.raw().write_uchar(encryptedData[i] ^ ord(self._key[i % len(self._key)][0]))
        else:
            self.raw().write_bytes(input_stram.read_bytes())

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

        for i in range(0, self._obj["backgroundsCount"]):
            bg = Fixture(self)
            ce.setObj(self._obj["backgroundFixtures"][i])
            self._obj["backgroundFixtures"][i] = bg

        for i in range(0, self._obj["foregroundsCount"]):
            fg = Fixture(self)
            fg.setObj(self._obj["foregroundsFixtures"][i])
            self._obj["foregroundsFixtures"][i] = fg

        for i in range(0, self._obj["layersCount"]):
            la = Layer(self, self._obj["mapVersion"])
            la.setObj(self._obj["layers"][i])
            self._obj["layers"][i] = la

        for i in range(0, self._obj["cellsCount"]):
            ce = CellData(self, i, self._obj["mapVersion"])
            ce.setObj(self._obj["cells"][i])
            self._obj["cells"][i] = ce

class Fixture:
    def __init__(self, parrent):
        self._parrent = parrent
        self._obj = OrderedDict()

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["fixtureId"] = self.raw().read_int32()
        self._obj["offsetX"]= self.raw().read_int16()
        self._obj["offsetY"] = self.raw().read_int16()
        self._obj["rotation"] = self.raw().read_int16()
        self._obj["xScale"] = self.raw().read_int16()
        self._obj["yScale"] = self.raw().read_int16()
        self._obj["redMultiplier"] = self.raw().read_char()
        self._obj["greenMultiplier"] = self.raw().read_char()
        self._obj["blueMultiplier"] =  self.raw().read_char()
        self._obj["hue"] = self._obj["redMultiplier"] | self._obj["greenMultiplier"] | self._obj["blueMultiplier"]
        self._obj["alpha"] =  self.raw().read_uchar()

    def write(self):
        self.raw().write_int32(self._obj["fixtureId"])
        self.raw().write_int16(self._obj["offsetX"])
        self.raw().write_int16(self._obj["offsetY"])
        self.raw().write_int16(self._obj["rotation"])
        self.raw().write_int16(self._obj["xScale"])
        self.raw().write_int16(self._obj["yScale"])
        self.raw().write_char(self._obj["redMultiplier"])
        self.raw().write_char(self._obj["greenMultiplier"])
        self.raw().write_char(self._obj["blueMultiplier"])
        self.raw().write_uchar(self._obj["alpha"])

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

class Layer:
    def __init__(self, parrent, mapVersion):
        self._parrent = parrent
        self._obj = OrderedDict()
        self.mapVersion = mapVersion

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["layerId"] = self.raw().read_int32()
        self._obj["cellsCount"] = self.raw().read_int16()
        self._obj["cells"] = []
        for i in range(0, self._obj["cellsCount"]):
            ce = Cell(self, self.mapVersion)
            ce.read()
            self._obj["cells"].append(ce.getObj())

    def write(self):
        self.raw().write_int32(self._obj["layerId"])
        self.raw().write_int16(self._obj["cellsCount"])
        for i in range(0, self._obj["cellsCount"]):
            self._obj["cells"][i].write()

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

        for i in range(0, self._obj["cellsCount"]):
            ce = Cell(self, self.mapVersion)
            ce.setObj(self._obj["cells"][i])
            self._obj["cells"][i] = ce

class Cell:
    def __init__(self, parrent, mapVersion):
        self._parrent = parrent
        self._obj = OrderedDict()
        self.mapVersion = mapVersion

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["cellId"] = self.raw().read_int16()
        self._obj["elementsCount"] = self.raw().read_int16()
        self._obj["elements"] = []
        for i in range(0, self._obj["elementsCount"]):
            el = BasicElement().GetElementFromType(self, self.raw().read_char(), self.mapVersion)
            el.read()
            self._obj["elements"].append(el.getObj())

    def write(self):
        self.raw().write_int16(self._obj["cellId"])
        self.raw().write_int16(self._obj["elementsCount"])

        for i in range(0, self._obj["elementsCount"]):
            if self._obj["elements"][i]._obj["elementName"] == "Graphical":
                self.raw().write_char(2)
            elif self._obj["elements"][i]._obj["elementName"] == "Sound":
                self.raw().write_char(33)
            else:
                raise InvalidDLMFile("Invalid element type.")

            self._obj["elements"][i].write()

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

        for i in range(0, self._obj["elementsCount"]):
            if self._obj["elements"][i]["elementName"] == "Graphical":
                el = GraphicalElement(self, self.mapVersion)
            elif self._obj["elements"][i]["elementName"] == "Sound":
                el = SoundElement(self, self.mapVersion)
            else:
                raise InvalidDLMFile("Invalid element type.")

            el.setObj(self._obj["elements"][i])
            self._obj["elements"][i] = el

class CellData:
    def __init__(self, parrent, id, mapVersion):
        self._parrent = parrent
        self._obj = OrderedDict()
        self.cellId = id
        self.mapVersion = mapVersion

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["floor"] = self.raw().read_char() # * 10
        self._obj["losmov"] = self.raw().read_uchar()
        self._obj["speed"] = self.raw().read_char()
        self._obj["mapChangeData"] = self.raw().read_uchar()

        if self.mapVersion > 5:
            self._obj["moveZone"] = self.raw().read_uchar()
        if self.mapVersion > 7:
            self._obj["tmpBits"] = self.raw().read_char()
            self.arrow = 15 & self._obj["tmpBits"]

            if self.useTopArrow():
                self._map.topArrowCell.append(self.cellId)

            if self.useBottomArrow():
                self._map.bottomArrowCell.append(self.cellId)

            if self.useLeftArrow():
                self._map.leftArrowCell.append(self.cellId)

            if self.useRightArrow():
                self._map.rightArrowCell.append(self.cellId)

    def write(self):
        self.raw().write_char(self._obj["floor"])
        self.raw().write_uchar(self._obj["losmov"])
        self.raw().write_char(self._obj["speed"])
        self.raw().write_uchar(self._obj["mapChangeData"])

        if self.mapVersion > 5:
            self.raw().write_uchar(self._obj["moveZone"])
        if self.mapVersion > 7:
            self.raw().write_char(self._obj["tmpBits"])

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

    def useTopArrow(self):
        if (self.arrow & 1) == 0:
            return False
        else:
            return True

    def useBottomArrow(self):
        if (self.arrow & 2) == 0:
            return False
        else:
            return True

    def useLeftArrow(self):
        if (self.arrow & 4) == 0:
            return False
        else:
            return True

    def useRightArrow(self):
        if (self.arrow & 8) == 0:
            return False
        else:
            return True

class BasicElement:
    def GetElementFromType(self, parrent, type, mapVersion):
        if type == 2: # GRAPHICAL
            return GraphicalElement(parrent, mapVersion)
        elif type == 33: # SOUND
            return SoundElement(parrent, mapVersion)
        else:
            raise InvalidDLMFile("Invalid element type.")

class GraphicalElement:
    def __init__(self, parrent, mapVersion):
        self._parrent = parrent
        self._obj = OrderedDict()
        self.mapVersion = mapVersion
        self._obj["elementName"] = "Graphical"

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["elementId"] = self.raw().read_uint32()

        # hue
        self._obj["hue_1"] = self.raw().read_char()
        self._obj["hue_2"] = self.raw().read_char()
        self._obj["hue_3"] = self.raw().read_char()

        # shadow
        self._obj["shadow_1"] = self.raw().read_char()
        self._obj["shadow_2"] = self.raw().read_char()
        self._obj["shadow_3"] = self.raw().read_char()

        if self.mapVersion <= 4:
            self._obj["offsetX"] = self.raw().read_char()
            self._obj["offsetY"] = self.raw().read_char()
        else:
            self._obj["offsetX"] = self.raw().read_int16()
            self._obj["offsetY"] = self.raw().read_int16()

        self._obj["altitude"] = self.raw().read_char()
        self._obj["identifier"] = self.raw().read_uint32()

    def write(self):
        self.raw().write_uint32(self._obj["elementId"])
        self.raw().write_char(self._obj["hue_1"])
        self.raw().write_char(self._obj["hue_2"])
        self.raw().write_char(self._obj["hue_3"])
        self.raw().write_char(self._obj["shadow_1"])
        self.raw().write_char(self._obj["shadow_2"])
        self.raw().write_char(self._obj["shadow_3"])

        if self.mapVersion <= 4:
            self.raw().write_char(self._obj["offsetX"])
            self.raw().write_char(self._obj["offsetY"])
        else:
            self.raw().write_int16(self._obj["offsetX"])
            self.raw().write_int16(self._obj["offsetY"])

        self.raw().write_char(self._obj["altitude"])
        self.raw().write_uint32(self._obj["identifier"])

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj

class SoundElement:
    def __init__(self, parrent, mapVersion):
        self._parrent = parrent
        self._obj = OrderedDict()
        self.mapVersion = mapVersion
        self._obj["elementName"] = "Sound"

    def raw(self):
        return self._parrent.raw()

    def read(self):
        self._obj["soundId"] = self.raw().read_int32()
        self._obj["baseVolume"] = self.raw().read_int16()
        self._obj["fullVolumeDistance"] = self.raw().read_int32()
        self._obj["nullVolumeDistance"] = self.raw().read_int32()
        self._obj["minDelayBetweenLoops"] = self.raw().read_int16()
        self._obj["maxDelayBetweenLoops"] = self.raw().read_int16()

    def write(self):
        self.raw().write_int32(self._obj["soundId"])
        self.raw().write_int16(self._obj["baseVolume"])
        self.raw().write_int32(self._obj["fullVolumeDistance"])
        self.raw().write_int32(self._obj["nullVolumeDistance"])
        self.raw().write_int16(self._obj["minDelayBetweenLoops"])
        self.raw().write_int16(self._obj["maxDelayBetweenLoops"])

    def getObj(self):
        return self._obj

    def setObj(self, obj):
        self._obj = obj
