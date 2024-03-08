import requests
import pandas as pd
import datetime
    
url = "http://localhost.com/api"
        

class DataGroup():
    data = {
        "field0" : [],
        "timestamp" : []
    }
    numFields = 1
    def __init__(self, numFields):
        pass

class Epoch():
    epochSize = 30 # Size of the epoch in seconds
    dataGroups = [] # List of data group objects to be displayed

    def __init__(self, dataGroups, epochSize):
        self.dataGroups = None



datetime.now()
response = requests.post(url, json=)