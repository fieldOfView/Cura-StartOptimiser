# Copyright (c) 2020 Aldo Hoeben / fieldOfView
# StartOptimiser is released under the terms of the AGPLv3 or higher.

from . import StartOptimiser

def getMetaData():
    return {}

def register(app):
    return {"extension": StartOptimiser.StartOptimiser()}
