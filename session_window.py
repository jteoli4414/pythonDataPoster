import time
from multiprocessing import  Queue
from PySide6 import QtCore, QtGui, QtWidgets
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget
from datetime import datetime, timedelta
from epoch_window import DataSet, Epoch
import copy

EPOCH_PERIOD = 30

class GraphWidget(QtCore.QThread):
    updateSignal = QtCore.Signal(list)

    def __init__(self,
                graphNames:list[str]=None,
                queueData:Queue=None,
                queueDb:Queue=None,
                queueEpoch:Queue=None):
        super().__init__()
        self.mainWidget = QtWidgets.QWidget()
        self.queueData = queueData
        self.queueDb = queueDb
        self.queueEpoch = queueEpoch
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        self.updateSignal.connect(self.updateUi)
        self.graphGroupingList = []
        self.isListening = False
        self.firstDataReceived = False
        self.toPost = []
        self.graphMapper = {}
        self.datasetMapper = {}
        self.epochs = []

        for graphName in graphNames:
            plot_widget = None
            plot_curve = None
            data_connector = None
            plot_widget = LivePlotWidget(title=(graphName))
            plot_curve = LiveLinePlot()
            plot_widget.addItem(plot_curve)
            data_connector = DataConnector(plot_curve, max_points=100, update_rate=144)
            self.mainLayout.addWidget(plot_widget)
            self.graphMapper[graphName] = data_connector
            self.datasetMapper[graphName] = []
    
        self.setupStateUi()
        self.mainLayout.addWidget(self.stateWidget)

    def setupStateUi(self):
        row = 0
        titleCol = 0
        valueCol = 1
        # Session State Widget
        self.stateWidget = QtWidgets.QWidget()
        self.stateLayout = QtWidgets.QGridLayout(self.stateWidget)

        ## State
        ### Session Start Time
        self.sessionStartTime = 0
        self.sessionStartTimeWidgetTitle = QtWidgets.QLabel("Session Start Time: ")
        self.stateLayout.addWidget(self.sessionStartTimeWidgetTitle, row, titleCol)
        self.sessionStartTimeWidget = QtWidgets.QLabel(str(self.sessionStartTime))
        self.stateLayout.addWidget(self.sessionStartTimeWidget, row, valueCol)
        row +=1

        ### Epochs Generated
        self.epochsGeneratedCounter = 0
        self.epochsGeneratedCounterWidgetTitle = QtWidgets.QLabel("Epochs Generated: ")
        self.stateLayout.addWidget(self.epochsGeneratedCounterWidgetTitle, row, titleCol)
        self.epochsGeneratedCounterWidget = QtWidgets.QLabel(str(self.epochsGeneratedCounter))
        self.stateLayout.addWidget(self.epochsGeneratedCounterWidget, row, valueCol)
        row +=1

    def run(self):
        self.isListening = True
        self.graphing()

    def die(self):
        self.isListening = False

    def timeFormat(self, timeTick):
        local_dt = datetime.fromtimestamp(timeTick)
        local_dt_est = local_dt + timedelta(hours=4)
        iso_format = local_dt_est.isoformat()
        return iso_format
    
    def timeFormatDatetime(self, timeTick):
        local_dt = datetime.fromtimestamp(timeTick)
        local_dt_est = local_dt + timedelta(hours=4)
        return local_dt_est 
    
    def createDataset(self, name, dataset):
        newlist = []
        for time, data in dataset:
            newlist.append([time, data])
        return DataSet(name, newlist)

    def createEpoch(self, startTime, period, datasets):
        newlist = []
        for data in datasets:
            newlist.append(data)
        return Epoch(startTime, period, newlist)

    def updateUi(self, data):
        value = data[0]
        graphTime = data[1]
        graphName = data[2]
        self.graphMapper[graphName].cb_append_data_point(value, graphTime)

        if(self.firstDataReceived == False):
            self.sessionStartTime = self.timeFormatDatetime(graphTime)
            self.currentEpochStartTime = graphTime
            self.sessionStartTimeWidget.setText(str(self.sessionStartTime))
            self.firstDataReceived = True

        self.datasetMapper[graphName].append([graphTime, value])

        elapsedTime = self.timeFormatDatetime(graphTime) - self.sessionStartTime
        # Epoch has passed dump data sets to Epoch object.
        if(elapsedTime > timedelta(seconds=EPOCH_PERIOD)):
            # Check if bad epoch (dataset length too small)
            createEpoch = False
            for name, dataset in self.datasetMapper.items():
                if(len(dataset) < 10):
                    createEpoch = False
                    break
                else:
                    createEpoch = True
            # If not bad epoch check to make sure all data size
            if(createEpoch):
                
                datasets = []
                for name, dataTuples in self.datasetMapper.items():
                    dataset = DataSet(name, copy.deepcopy(dataTuples))
                    datasets.append(dataset)
                    dataset = []
                    self.datasetMapper[name] = []
                newEpoch = Epoch(self.sessionStartTime, self.timeFormatDatetime(graphTime), EPOCH_PERIOD, copy.deepcopy(datasets))
                self.queueEpoch.put(copy.deepcopy(newEpoch))
                self.epochsGeneratedCounter += 1
                self.epochsGeneratedCounterWidget.setText(str(self.epochsGeneratedCounter))
                
            self.sessionStartTime = self.timeFormatDatetime(graphTime)

    def graphing(self):
        while(self.isListening):
            if(self.queueData.empty() == False):
                data = self.queueData.get()
                self.updateSignal.emit(data)
                self.queueDb.put([data[0], data[1], data[2]])
            time.sleep(0.001)