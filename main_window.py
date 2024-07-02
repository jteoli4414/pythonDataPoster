import time
from multiprocessing import Queue

from dreamband_connector import DreamBandHandler
from influx_connector import InfluxConnector
from ble_window import BLEControlWidget, BLEStatsWidget
from db_window import DBControlWidget, DBStatsWidget
from session_window import GraphWidget
from epoch_window import EpochWidget

import sys
from PySide6 import QtCore, QtGui, QtWidgets

class MainWidget(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupQueues()
        self.setupUi()
        self.startThreads()

    def setupQueues(self):
        self.bleDataQueue = Queue()
        self.bleEventQueue = Queue()
        self.bleControlQueue = Queue()
        self.influxDbQueue = Queue()
        self.influxEventQueue = Queue()
        self.influxControlQueue = Queue()
        self.epochQueue = Queue()

    def setupRecordingSessionUi(self):
        self.dataTab = QtWidgets.QWidget()
        self.dataLayout = QtWidgets.QVBoxLayout(self.dataTab)
        # Setup Graph
        self.graphs = ["EOG","Accel X","Accel Y","Accel Z","Red Light","IR Light"]
        self.graph = GraphWidget(self.graphs, self.bleDataQueue, self.influxDbQueue, self.epochQueue)
        self.dataLayout.addWidget(self.graph.mainWidget)
        self.tabs.addTab(self.dataTab, "Recording Session")

    def setupBleTabUi(self):
        # Setup BLE Tab Plane
        self.ble_handler = DreamBandHandler(self.bleDataQueue, self.bleEventQueue, self.bleControlQueue)
        self.bleTab = QtWidgets.QWidget()
        self.bleLayout = QtWidgets.QHBoxLayout(self.bleTab)
        self.bleControl = BLEControlWidget(self.bleControlQueue)
        self.bleStats  = BLEStatsWidget(self.bleEventQueue)
        self.bleLayout.addWidget(self.bleControl)
        self.bleLayout.addWidget(self.bleStats.mainWidget)
        self.tabs.addTab(self.bleTab, "Mask Control")

    def setupDbTabUi(self):
        ## Setup DB Tab Plane
        self.db_connector = InfluxConnector(self.influxDbQueue, self.influxEventQueue, self.influxControlQueue)
        self.dbTab = QtWidgets.QWidget()
        self.dbLayout = QtWidgets.QHBoxLayout(self.dbTab)
        self.dbControl = DBControlWidget(self.influxControlQueue)
        self.dbStats = DBStatsWidget(self.influxEventQueue)
        self.dbLayout.addWidget(self.dbControl)
        self.dbLayout.addWidget(self.dbStats.mainWidget)
        self.tabs.addTab(self.dbTab, "Influx Poster")

    def setupEpochTabUi(self):
        self.epochTab = QtWidgets.QWidget()
        self.epochLayout = QtWidgets.QVBoxLayout(self.epochTab)
        self.epochWindow = EpochWidget(self.epochQueue, self.graphs)
        self.epochLayout.addWidget(self.epochWindow.mainWidget)
        self.tabs.addTab(self.epochTab, "Epoch Analyzer")

    def setupUi(self):
        self.setWindowTitle(f"DreamBand Controller")
        self.tabs = QtWidgets.QTabWidget()

        self.setupBleTabUi()
        self.setupDbTabUi()
        self.setupRecordingSessionUi()
        self.setupEpochTabUi()

        self.setCentralWidget(self.tabs)

    def startThreads(self):
        self.ble_handler.start()
        self.bleStats.start()
        self.db_connector.start()
        self.dbStats.start()
        self.graph.start()
        self.epochWindow.start()


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainMenu = MainWidget(None)
    mainMenu.show()
    app.exec()

if __name__ == "__main__":
    main()
