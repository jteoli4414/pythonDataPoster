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

EPOCH_PERIOD = 30

class DataSet():
    def __init__(self, name, tuples):
        self.datasetName = name
        self.timeTuples = tuples

    def return_x(self):
        ret = []
        for tuple in self.timeTuples:
            ret.append(tuple[0])
        return ret
    
    def return_y(self):
        ret = []
        for tuple in self.timeTuples:
            ret.append(tuple[1])
        return ret
    
class Epoch():
    def __init__(self, startTime, stopTime, periodLength, datasets:list[DataSet]):
        self.datasets = datasets
        self.startTime = startTime
        self.periodLength = periodLength
        self.stopTime = stopTime

class EpochWidget(QtCore.QThread):
    updateSignal = QtCore.Signal(Epoch)

    def __init__(self,
                 epochQueue:Queue,
                 graphNames:list[str]=None):
        super().__init__()
        self.mainWidget = QtWidgets.QWidget()
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        self.graphNames = graphNames
        self.updateSignal.connect(self.updateUi)

        self.isListening = False

        self.epochQueue = epochQueue
        self.epochMapper = {}
        self.datasetMapper = {}
        self.graphMapper = {}

        self.currentEpochNumber = 0
        
        # Setup Graphs
        self.setupEpochGraphUi()
        self.mainLayout.addWidget(self.epochGraphWidget)

        # Setup Selection Bar Ui
        self.selectWidget = QtWidgets.QWidget()
        self.selectWidgetLayout = QtWidgets.QHBoxLayout(self.selectWidget)

        self.setupSelectEpochUi()
        self.selectWidgetLayout.addWidget(self.epochSelectWidget)

        self.setupExportEpochUi()
        self.selectWidgetLayout.addWidget(self.epochExportWidget)

        self.mainLayout.addWidget(self.selectWidget)


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

    def setupExportEpochUi(self):
        self.epochExportWidget = QtWidgets.QWidget()
        self.epochExportWidgetLayout = QtWidgets.QVBoxLayout(self.epochExportWidget)

        self.outputDirectoryTitleWidget = QtWidgets.QLabel("Exporting to: (Directory not specified)")
        self.epochExportWidgetLayout.addWidget(self.outputDirectoryTitleWidget)
        
        self.epochOutputDirectoryButtonWidget = QtWidgets.QPushButton("Set Output Directory")
        self.epochOutputDirectoryButtonWidget.clicked.connect(self.onEpochOutputDirectoryButtonClicked)
        self.epochExportWidgetLayout.addWidget(self.epochOutputDirectoryButtonWidget)
        
        self.epochExportButtonWidget = QtWidgets.QPushButton("Export Epoch")
        self.epochExportButtonWidget.clicked.connect(self.onEpochExportButtonClicked)
        self.epochExportWidgetLayout.addWidget(self.epochExportButtonWidget)

        self.outputDirectorySelected = False

    def onEpochOutputDirectoryButtonClicked(self):
        self.outputDirectoryDialog = QtWidgets.QFileDialog()
        self.outputDirectoryDialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        self.outputDirectory = self.outputDirectoryDialog.getExistingDirectory()
        if(self.outputDirectory != ""):
            self.outputDirectorySelected = True
            outputString = "Exporting to: " + self.outputDirectory
            self.outputDirectoryTitleWidget.setText(outputString)

    def onEpochExportButtonClicked(self):
        fileName = "Dreamband_" +self.epochDropBoxWidget.currentText().replace(" ", "_").replace(":", "").replace(".", "_") + ".csv"
        if(self.outputDirectorySelected):
            absFilePath = self.outputDirectory + "/" + fileName
            absFilePath = absFilePath.replace("/", "\\")
            with open(absFilePath, "w", newline='') as csvFile:

                currentEpoch = self.epochMapper[self.epochDropBoxWidget.currentIndex()]
                fieldNames = []
                fieldNameContentsMapper = {}
                for dataset in currentEpoch.datasets:
                    timeFieldName = "Time_"+ dataset.datasetName
                    dataFieldName = "Data_"+ dataset.datasetName
                    fieldNames.append(timeFieldName)
                    fieldNames.append(dataFieldName)
                    fieldNameContentsMapper[timeFieldName] = dataset.return_x()
                    fieldNameContentsMapper[dataFieldName] = dataset.return_y()
                
                rows = {}
                counter = 0
                # Set the counter dicts
                for fieldName, content in fieldNameContentsMapper.items():
                    for dataPoint in content:
                        rows[counter] = {}
                        counter+=1
                    counter = 0

                # Set the fields
                for fieldName, content in fieldNameContentsMapper.items():
                    for dataPoint in content:
                        rows[counter][fieldName] = dataPoint
                        counter+=1
                    counter = 0

                writer = csv.DictWriter(csvFile, fieldnames=fieldNames)
                writer.writeheader()
                for _, row in rows.items():
                    writer.writerow(row)

        else:
            self.showError("Output directory not specified.")

    def showError(self, error):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setText("Error")
        msg.setInformativeText(error)
        msg.setWindowTitle("Error")

    def setupSelectEpochUi(self):
        self.epochSelectWidget = QtWidgets.QWidget()
        self.epochSelectWidgetLayout = QtWidgets.QHBoxLayout(self.epochSelectWidget)

        self.epochTitleWidget = QtWidgets.QLabel("Select Epoch: ")
        self.epochDropBoxWidget = QtWidgets.QComboBox()
        # User cannot edit this box
        self.epochDropBoxWidget.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.epochDropBoxWidget.currentIndexChanged.connect(self.onEpochSelection)

        self.epochSelectWidgetLayout.addWidget(self.epochTitleWidget)
        self.epochSelectWidgetLayout.addWidget(self.epochDropBoxWidget)



    def graphEpoch(self, epochNumber):
        # set all graph data
        currentEpoch = self.epochMapper[int(epochNumber)]
        for dataset in currentEpoch.datasets:
            xVals = dataset.return_x()
            yVals = dataset.return_y()
            self.graphMapper[dataset.datasetName].cb_set_data(yVals, xVals)

    def onEpochSelection(self, epochNumber):
        self.graphEpoch(epochNumber)

    def run(self):
        self.isListening = True
        self.listening()

    def die(self):
        self.isListening = False
    
    def updateUi(self, epoch:Epoch):
        self.epochMapper[self.currentEpochNumber] = epoch
        epochString = "Epoch: "+ str(self.currentEpochNumber)+ " " + epoch.stopTime.isoformat()
        self.epochDropBoxWidget.insertItem(self.currentEpochNumber, epochString)
        self.currentEpochNumber += 1
        self.containsEpochs = True

    def listening(self):
        while(self.isListening):
            if(self.epochQueue.empty() == False):
                data = self.epochQueue.get()
                self.updateSignal.emit(data)
            time.sleep(0.001)

class EpochAnalyzeAccelerometer():
      pass