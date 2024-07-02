import time
from multiprocessing import  Queue
from PySide6 import QtCore, QtGui, QtWidgets
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget
from datetime import datetime, timedelta
import copy
import numpy as np
import csv

import pyqtgraph as pg
import numpy as np


class ImportEpochWidget(QtCore.QThread):

    def __init__(self,
                 epochQueue:Queue,
                 graphNames:list[str]=None):
        super().__init__()
        self.mainWidget = QtWidgets.QWidget()
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        self.graphNames = graphNames

        self.epochQueue = epochQueue
        self.epochMapper = {}
        self.datasetMapper = {}
        self.graphMapper = {}
        
        self.setupAnalyzeEpochSelectionUi()
        self.mainLayout.addWidget(self.analyzeEpochSelectionWidget)

        self.setupAnalysisTabUi()
        self.mainLayout.addWidget(self.analysisTabs)

    def setupAnalyzeEpochSelectionUi(self):
        self.analyzeEpochSelectionWidget = QtWidgets.QWidget()
        self.analyzeEpochSelectionLayout = QtWidgets.QHBoxLayout(self.analyzeEpochSelectionWidget)

        self.analyzeButtonWidget = QtWidgets.QPushButton("Analyze")
        self.analyzeButtonWidget.clicked.connect(self.onAnalyzeButtonClicked)

        self.importEpochButtonWidget = QtWidgets.QPushButton("Import Epoch")
        self.importEpochButtonWidget.clicked.connect(self.onImportEpochButtonClicked)

        self.analyzeEpochSelectionLayout.addWidget(self.analyzeButtonWidget)
        self.analyzeEpochSelectionLayout.addWidget(self.importEpochButtonWidget)

    def setupAnalysisTabUi(self):
        self.analysisTabs = QtWidgets.QTabWidget()
        self.setupEpochGraphUi()
        self.analysisTabs.addTab(self.epochGraphWidget, "Raw Epoch Data")

        self.setupAccelerometerTab()

    def setupAccelerometerTab(self):
        self.accelerometerFFTWidget = QtWidgets.QWidget()
        self.accelerometerFFTLayout = QtWidgets.QHBoxLayout(self.accelerometerFFTWidget)

        plotWidgetAccelX = LivePlotWidget(title=(graphName))
        plotCurveAccelX = LivePlotWidget(title=(graphName))
        dataConnectorAccelX = LivePlotWidget(title=(graphName))




    def setupEpochGraphUi(self):
        self.epochGraphWidget = QtWidgets.QWidget()
        self.epochGraphWidgetLayout = QtWidgets.QVBoxLayout(self.epochGraphWidget)
        
        for graphName in self.graphNames:
            plot_widget = None
            plot_curve = None
            data_connector = None
            plot_widget = LivePlotWidget(title=(graphName))
            plot_curve = LiveLinePlot()
            plot_widget.addItem(plot_curve)
            data_connector = DataConnector(plot_curve, update_rate=144)
            self.containsEpochs = False
            self.epochGraphWidgetLayout.addWidget(plot_widget)
            self.graphMapper[graphName] = data_connector
            self.datasetMapper[graphName] = []



    def onAnalyzeButtonClicked(self):
        pass

    def onImportEpochButtonClicked(self):
        self.importEpochFileDialog = QtWidgets.QFileDialog()
        self.importEpochFileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        self.epochFile = self.importEpochFileDialog.getOpenFileName()
        if(self.epochFile != ""):
            self.epochFileSelected = True


    def graphEpoch(self, epochNumber):
        # set all graph data
        currentEpoch = self.epochMapper[int(epochNumber)]
        for dataset in currentEpoch.datasets:
            xVals = dataset.return_x()
            yVals = dataset.return_y()
            self.graphMapper[dataset.datasetName].cb_set_data(yVals, xVals)

    def onEpochSelection(self, epochNumber):
        self.graphEpoch(epochNumber)

    def updateUi(self, epoch:Epoch):
        self.epochMapper[self.currentEpochNumber] = epoch
        epochString = "Epoch: "+ str(self.currentEpochNumber)+ " " + epoch.stopTime.isoformat()
        self.epochDropBoxWidget.insertItem(self.currentEpochNumber, epochString)
        self.currentEpochNumber += 1
        self.containsEpochs = True

class EpochAnalyzeAccelerometer():
      pass