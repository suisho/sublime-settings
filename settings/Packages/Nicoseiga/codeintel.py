#!/usr/bin/env python
# Copyright (c) 2006-2008 ActiveState Software Inc.
# See LICENSE.txt for license details.

import os
import sys
import logging
import re
import threading
import codeintel2

from datetime import datetime
#from xpcom.server import UnwrapObject

import ciElementTree as ET

log = logging.getLogger("coets")
log.setLevel(logging.DEBUG)
log.info(datetime.now())
#timer = threading.Timer(1)

def analyseInstance(text,type):
    method = "get"+type
    regex = method+'\([\'"](.+)?[\'"]\)'
    rx = re.compile(regex)
    list = rx.findall(text)
    if len(list) > 0:
        ins = list[len(list)-1]
        ins = ins[0].upper() + ins[1:] + type
        return ins

def addCodeintel(child):
    types = ["Model","Dao"]
    scimoz = komodo.editor
    text = scimoz.text[0:scimoz.anchor]#.replace('\r','').split('\n')
    for type in types:
        _name = "get"+type
        _returns = analyseInstance(text,type)
        if _returns:
            log.debug(_name+":"+_returns)
            method = ET.SubElement(child, "scope", ilk="function",
                                          name=_name,line=0,
                                          returns=_returns)
try:
    if hasattr(komodo.document, "ciBuf"):
        buf = UnwrapObject(komodo.document.ciBuf)
        blob = buf.blob_from_lang["PHP"]

        for child in blob:            
            if child.get('ilk') == 'class':
                log.debug(child)
                addCodeintel(child)
            
except Exception, ex:
    import traceback
    traceback.print_exc()
