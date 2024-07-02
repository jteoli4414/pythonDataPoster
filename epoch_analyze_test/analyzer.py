import numpy as np
import csv
import time
from multiprocessing import Queue
import sys
from PySide6 import QtCore, QtGui, QtWidgets
from scipy.signal import lombscargle
from scipy.interpolate import interp1d

import pyqtgraph as pg
import numpy as np

class ImportEpochWidget(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.mainWidget = QtWidgets.QWidget()
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)

        self.setupAnalyzeEpochSelectionUi()
        self.mainLayout.addWidget(self.analyzeEpochSelectionWidget)

        self.setupAnalysisTabUi()
        self.mainLayout.addWidget(self.analysisTabs)

        # Logging
        self.loggingWidget = QtWidgets.QTextBrowser()
        self.mainLayout.addWidget(self.loggingWidget)

        self.setCentralWidget(self.mainWidget)


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

        self.setupLombscargleGraphUi()
        self.analysisTabs.addTab(self.lombscargleGraphWidget, "Lombscargle Computed")


        self.setupAccelerometerTab()
        self.analysisTabs.addTab(self.accelerometerFFTWidget, "Accel Analysis")

    def setupLombscargleGraphUi(self):
        self.lombscargleGraphWidget = QtWidgets.QWidget()
        self.lombscargleGraphWidgetLayout = QtWidgets.QVBoxLayout(self.lombscargleGraphWidget)

        self.lomEogGraph = pg.PlotWidget()
        self.lomEogGraph.plotItem.setTitle("Lombscargle EOG Sensor")
        self.lomEogGraph.plotItem.setLabel('left', "Voltage ADC")
        self.lomEogGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomEogGraph)

        self.lomAccelXGraph = pg.PlotWidget()
        self.lomAccelXGraph.plotItem.setTitle("Lombscargle Accelerometer X Sensor")
        self.lomAccelXGraph.plotItem.setLabel('left', "m/s^2")
        self.lomAccelXGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomAccelXGraph)

        self.lomAccelYGraph = pg.PlotWidget()
        self.lomAccelYGraph.plotItem.setTitle("Lombscargle Accelerometer Y Sensor")
        self.lomAccelYGraph.plotItem.setLabel('left', "m/s^2")
        self.lomAccelYGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomAccelYGraph)

        self.lomAccelZGraph = pg.PlotWidget()
        self.lomAccelZGraph.plotItem.setTitle("Lombscargle Accelerometer Z Sensor")
        self.lomAccelZGraph.plotItem.setLabel('left', "m/s^2")
        self.lomAccelZGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomAccelZGraph)

        self.lomRedGraph = pg.PlotWidget()
        self.lomRedGraph.plotItem.setTitle("Lombscargle Red Light")
        self.lomRedGraph.plotItem.setLabel('left', "Voltage Level ADC")
        self.lomRedGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomRedGraph)

        self.lomIrGraph = pg.PlotWidget()
        self.lomIrGraph.plotItem.setTitle("Lombscargle IR Light")
        self.lomIrGraph.plotItem.setLabel('left', "Voltage Level ADC")
        self.lomIrGraph.plotItem.setLabel('bottom', "Hz")
        self.lombscargleGraphWidgetLayout.addWidget(self.lomIrGraph)

    def lombscargleData(self, x, y, plot):
        n = len(x)
        duration = x.ptp()
        freqs = np.linspace(1/duration, n/duration, 5*n) / 2*3.141592
        periodogram = lombscargle(x, y, freqs)
        #kmax = periodogram.argmax()
        plot.plotItem.plot(freqs, np.sqrt(4*periodogram/(5*n)))
    
    def interpolateData(self, x, y, plot):
        predict = interp1d(x, y, kind="quadratic")
        X2 = np.linspace(x[0], x[len(x)-1], 10000)
        Y2 = np.array([predict(x) for x in X2])
        plot.plotItem.plot(X2, Y2)


    def setupAccelerometerTab(self):
        self.accelerometerFFTWidget = QtWidgets.QWidget()
        self.accelerometerFFTLayout = QtWidgets.QHBoxLayout(self.accelerometerFFTWidget)
        self.fftPlotWidgetAccelX = pg.PlotWidget()
        self.fftPlotWidgetAccelY = pg.PlotWidget()
        self.fftPlotWidgetAccelZ = pg.PlotWidget()
        self.accelerometerFFTLayout.addWidget(self.fftPlotWidgetAccelX)
        self.accelerometerFFTLayout.addWidget(self.fftPlotWidgetAccelY)
        self.accelerometerFFTLayout.addWidget(self.fftPlotWidgetAccelZ)

    def onAnalyzeButtonClicked(self):
        self.interpolateData(self.npTimeEog, self.npValEog, self.lomEogGraph)
        self.interpolateData(self.npTimeAccelX, self.npValAccelX, self.lomAccelXGraph)
        self.interpolateData(self.npTimeAccelY, self.npValAccelY, self.lomAccelYGraph)
        self.interpolateData(self.npTimeAccelZ, self.npValAccelZ, self.lomAccelZGraph)
        self.interpolateData(self.npTimeIr, self.npValIr, self.lomRedGraph)
        self.interpolateData(self.npTimeRed, self.npValRed, self.lomIrGraph)



    def setupEpochGraphUi(self):
        self.epochGraphWidget = QtWidgets.QWidget()
        self.epochGraphWidgetLayout = QtWidgets.QVBoxLayout(self.epochGraphWidget)

        self.epochEogGraph = pg.PlotWidget()
        self.epochEogGraph.plotItem.setTitle("EOG Sensor")
        self.epochEogGraph.plotItem.setLabel('left', "Voltage ADC")
        self.epochEogGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochEogGraph)

        self.epochAccelXGraph = pg.PlotWidget()
        self.epochAccelXGraph.plotItem.setTitle("Accelerometer X Sensor")
        self.epochAccelXGraph.plotItem.setLabel('left', "m/s^2")
        self.epochAccelXGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochAccelXGraph)

        self.epochAccelYGraph = pg.PlotWidget()
        self.epochAccelYGraph.plotItem.setTitle("Accelerometer Y Sensor")
        self.epochAccelYGraph.plotItem.setLabel('left', "m/s^2")
        self.epochAccelYGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochAccelYGraph)

        self.epochAccelZGraph = pg.PlotWidget()
        self.epochAccelZGraph.plotItem.setTitle("Accelerometer Z Sensor")
        self.epochAccelZGraph.plotItem.setLabel('left', "m/s^2")
        self.epochAccelZGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochAccelZGraph)

        self.epochRedGraph = pg.PlotWidget()
        self.epochRedGraph.plotItem.setTitle("Red Light")
        self.epochRedGraph.plotItem.setLabel('left', "Voltage Level ADC")
        self.epochRedGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochRedGraph)

        self.epochIrGraph = pg.PlotWidget()
        self.epochIrGraph.plotItem.setTitle("IR Light")
        self.epochIrGraph.plotItem.setLabel('left', "Voltage Level ADC")
        self.epochIrGraph.plotItem.setLabel('bottom', "Ticks")
        self.epochGraphWidgetLayout.addWidget(self.epochIrGraph)
        
    def onImportEpochButtonClicked(self):
        self.importEpochFileDialog = QtWidgets.QFileDialog()
        self.importEpochFileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        self.epochFile = self.importEpochFileDialog.getOpenFileName()[0]
        if(self.epochFile != ""):
            self.epochFileSelected = True
            toLog = "Importing Epoch: " + self.epochFile
            self.loggingWidget.append(toLog)

            self.ingestEpoch()

    def ingestEpoch(self):
        self.eogTimeList = []
        self.eogValList = []

        self.AccelXTimeList = []
        self.AccelXValList = []

        self.AccelYTimeList = []
        self.AccelYValList = []

        self.AccelZTimeList = []
        self.AccelZValList = []

        self.redTimeList = []
        self.redValList = []

        self.irTimeList = []
        self.irValList = []   

        with open(self.epochFile, 'r') as fp:
            self.data = np.genfromtxt(self.epochFile, delimiter=',')

            lines = fp.readlines()
            for x in range (1,len(lines)):
                line = lines[x]
                lineParts = line.split(",")
                self.eogTimeList.append(float(lineParts[0]))
                self.eogValList.append(float(lineParts[1]))

                self.AccelXTimeList.append(float(lineParts[2]))
                self.AccelXValList.append(float(lineParts[3]))

                self.AccelYTimeList.append(float(lineParts[4]))
                self.AccelYValList.append(float(lineParts[5]))

                self.AccelZTimeList.append(float(lineParts[6]))
                self.AccelZValList.append(float(lineParts[7]))

                self.redTimeList.append(float(lineParts[8]))
                self.redValList.append(float(lineParts[9]))

                self.irTimeList.append(float(lineParts[10]))
                self.irValList.append(float(lineParts[11]))

        self.npTimeEog = np.array(self.eogTimeList)
        self.npTimeAccelX = np.array(self.AccelXTimeList)
        self.npTimeAccelY = np.array(self.AccelYTimeList)
        self.npTimeAccelZ = np.array(self.AccelZTimeList)
        self.npTimeRed = np.array(self.redTimeList)
        self.npTimeIr = np.array(self.irTimeList)

        self.npValEog = np.array(self.eogValList)
        self.npValAccelX = np.array(self.AccelXValList)
        self.npValAccelY = np.array(self.AccelYValList)
        self.npValAccelZ = np.array(self.AccelZValList)
        self.npValRed = np.array(self.redValList)
        self.npValIr = np.array(self.irValList)
        
        self.epochEogGraph.plotItem.plot(self.npTimeEog, self.npValEog)
        self.epochAccelXGraph.plotItem.plot(self.npTimeAccelX, self.npValAccelX)
        self.epochAccelYGraph.plotItem.plot(self.npTimeAccelY, self.npValAccelY)
        self.epochAccelZGraph.plotItem.plot(self.npTimeAccelZ, self.npValAccelZ)
        self.epochIrGraph.plotItem.plot(self.npTimeRed, self.npValRed)
        self.epochRedGraph.plotItem.plot(self.npTimeIr, self.npValIr)


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainMenu = ImportEpochWidget()
    mainMenu.show()
    app.exec()

if __name__ == "__main__":
    main()
