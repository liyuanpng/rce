#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       SerializerUtil.py
#       
#       Copyright 2012 dominique hunziker <dominique.hunziker@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#       
#       

# Python specific imports
from struct import Struct, error as StructError

# Custom imports
from Exceptions import SerializationError
import MsgDef
from FIFO import MessageFIFO

# None
_NONE = '__None__'
_NONE_LEN = len(_NONE)

# Bool
_B_STRUCT = Struct('!B')
_B_LEN = _B_STRUCT.size

# Integer
_I_STRUCT = Struct('!I')
_I_LEN = _I_STRUCT.size

# Float
_F_STRUCT = Struct('!d')
_F_LEN = _F_STRUCT.size

class Serializer(object):
    """ Class which is used to serialize a message.
    """
    def __init__(self, buf=MessageFIFO()):
        """ Initialize the Serializer.
            
            @param buf:     FIFO into which the message should be serialized.
            @type  buf:     MessageFIFO
        """
        self._buf = buf
    
    def addHeader(self, length, dest, origin, msgType, msgNr):
        """ Serialize a header.
            
            This method should not be used directly by the content serializers!
        """
        self._buf.pushFront(_I_STRUCT.pack(msgNr))
        self._buf.pushFront(msgType)
        self._buf.pushFront(origin)
        self._buf.pushFront(dest)
        self._buf.pushFront(_I_STRUCT.pack(length))
    
    def addBool(self, b):
        """ Serialize a single boolean.
            
            @param b:   Boolean which should be serialized.
            @type  b:   bool
        """
        self._buf.push(_B_STRUCT.pack(b))
    
    def addInt(self, i):
        """ Serialize a single integer.
            
            @param i:   Integer which should be serialized.
            @type  i:   int
        """
        self._buf.push(_I_STRUCT.pack(i))
    
    def addFloat(self, f):
        """ Serialize a single float.
            
            @param f:   Float which should be serialized.
            @type  f:   float
        """
        self._buf.push(_F_STRUCT.pack(f))
    
    def addElement(self, element):
        """ Serialize a single element.
            
            @param element:     Element which should be serialized.
            @type  element:     str / None
            
            @raise:     TypeError if the element is not of type str or of type None.
        """
        if element is None:
            self._buf.push(_NONE_LEN)
            self._buf.push(_NONE)
        elif isinstance(element, str):
            self.addInt(len(element))
            self._buf.push(element)
        else:
            raise TypeError('Element is neither of type str nor of type None.')
    
    def addDict(self, data):
        """ Serialize the dictionary.
    
            @param data:    Dictionary which should be serialized.
            @type  data:    { str / None : str / None }
    
            @raise:         SerializationError if content is not a dictionary.
        """
        self.addInt(len(data))
        
        for (key, value) in data.iteritems():
            try:
                self.addElement(key)
            except TypeError:
                raise SerializationError('Key is neither a of type str nor of type None.')
            
            try:
                self.addElement(value)
            except TypeError:
                raise SerializationError('Value is neither a of type str nor of type None.')
    
    def addList(self, data):
        """ Serialize the list.
    
            @param data:    List which should be serialized.
            @type  data:    [ str / None ]
    
            @raise:         SerializationError if content is not a list.
        """
        self.addInt(len(data))
    
        for element in data:
            self.addElement(element)
    
    def addFIFO(self, fifo):
        """ Add the serialized data of the FIFO to the current FIFO..
    
            @param data:    FIFO containing serialized data which should be added.
            @type  data:    MessageFIFO
    
            @raise:         SerializationError if content is not a MessageFIFO.
        """
        if not isinstance(fifo, MessageFIFO):
            raise SerializationError('fifo is not of type MessageFIFO.')
        
        buf = fifo.getMsg()
        self.addInt(len(buf))
        self._buf += buf
    
    def addCustom(self, data, serializer):
        """ Serialize the custom component.
            
            @param data:    Custom component which should be serialized.
            @type  data:    Arbitrary
            
            @param serializer:  Serializer class which should be used to serialize the
                                custom component.
            @type  serializer:  IContentSerializer (IDENTIFIER will be ignored.)
    
            @raise:         SerializationError may be raised by the serializer.
        """
        serializer.serialize(self._buf, data)
    
    def getMsg(self):
        """ Get the message which has been assembled until now.
            
            @return:    Serialized message.
            @rtype:     MessageFIFO
        """
        return self._buf

class Deserializer(object):
    """ Class which is used to deserialize a message.
    """
    def __init__(self, fifo):
        """ Initialize the Deserializer.
    
            @param fifo:    Serialized data.
            @type  fifo:    MessageFIFO
        """
        self._buf = fifo
    
    def getHeader(self):
        """ Serialize a header.
            
            This method should not be used directly by the content serializers!
        """
        length = _I_STRUCT.unpack(self._buf.pop(_I_LEN)[0])[0]
        dest = self._buf.pop(MsgDef.ADDRESS_LENGTH)[0]
        origin = self._buf.pop(MsgDef.ADDRESS_LENGTH)[0]
        msgType = self._buf.pop(MsgDef.MSG_TYPE_LENGTH)[0]
        msgNr = _I_STRUCT.unpack(self._buf.pop(_I_LEN)[0])[0]
        return (length, dest, origin, msgType, msgNr)
    
    def getBool(self):
        """ Deserialize a single boolean.
            
            @return:    Deserialized boolean.
            @rtype:     bool
        """
        try:
            data, n = self._buf.pop(_B_LEN)
            
            if n != _B_LEN:
                raise SerializationError('There is not enough data left.')
            
            return _B_STRUCT.unpack(data)[0]
        except StructError as e:
            raise SerializationError('Data is not a valid boolean: {0}'.format(e))

    def getInt(self):
        """ Deserialize a single integer.
            
            @return:    Deserialized integer.
            @rtype:     int
        """
        try:
            data, n = self._buf.pop(_I_LEN)
            
            if n != _I_LEN:
                raise SerializationError('There is not enough data left.')
            
            return _I_STRUCT.unpack(data)[0]
        except StructError as e:
            raise SerializationError('Data is not a valid integer: {0}'.format(e))

    def getFloat(self):
        """ Deserialize a single float.
            
            @return:    Deserialized float.
            @rtype:     float
        """
        try:
            data, n = self._buf.pop(_F_LEN)
            
            if n != _F_LEN:
                raise SerializationError('There is not enough data left.')
            
            return _F_STRUCT.unpack(data)[0]
        except StructError as e:
            raise SerializationError('Data is not a valid float: {0}'.format(e))
    
    def getElement(self):
        """ Deserialize a single element.
            
            @return:    Deserialized element.
            @rtype:     str / None
        """
        length = self.getInt()    
        element, n = self._buf.pop(length)
        
        if n != length:
            raise SerializationError('There is not enough data left.')
        
        if length == _NONE_LEN and element == _NONE:
            element = None
        
        return element
    
    def getDict(self):
        """ Deserialize the data.
    
            @return:        Dictionary of the message.
            @rtype:         { str / None : str / None }
        """
        return dict((self.getElement(), self.getElement()) for _ in xrange(self.getInt()))
    
    def getList(self):
        """ Deserialize the data.
    
            @return:        List of the message.
            @rtype:         [ str / None ]
            
            @raise:     SerializationError if the format does not match that of a
                        serialized list.
        """
        return [self.getElement() for _ in xrange(self.getInt())]
    
    def addCustom(self, serializer):
        """ Deserialize the custom component.
            
            @param serializer:  Serializer class which should be used to deserialize the
                                custom component.
            @type  serializer:  IContentSerializer (IDENTIFIER will be ignored.)
            
            @return:    Custom component.
            @rtype:     Arbitrary
    
            @raise:         SerializationError may be raised by the serializer.
        """
        return serializer.deserialize(self._buf)
