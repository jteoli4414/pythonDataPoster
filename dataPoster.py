import time
from multiprocessing import Process, Queue

import time
import DreamBand
import InfluxConnector
import sys
from threading import Thread
from PyQt5 import QtCore, QtGui, QtWidgets
from pglive.kwargs import Axis
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_axis import LiveAxis
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

# Graphing Variables

class GraphWidget(QtWidgets.QWidget):
    
    def __init__(self,
                parent=None,
                graphNames:list[str]=None):
        super().__init__(parent)

        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.graphGroupingList = []
        self.running = True
        self.toPost = []
        self.graphMapper = {}


        for graphName in graphNames:
            plot_widget = None
            plot_curve = None
            data_connector = None
            plot_widget = LivePlotWidget(title=(graphName))
            plot_curve = LiveLinePlot()
            plot_widget.addItem(plot_curve)
            data_connector = DataConnector(plot_curve, max_points=600, update_rate=144)
            self.mainLayout.addWidget(plot_widget)
            self.graphMapper[graphName] = data_connector

    def start_graphing(self, queueData:Queue, queueDb:Queue):
        self.running = True
        self.graphing(queueData, queueDb)

    def stop_graphing(self):
        self.running = False

    def graphing(self, queueData:Queue, queueDb:Queue):
        self.running = True
        while(self.running):
            if(queueData.empty() == False):
                to_graph = queueData.get()
                value = to_graph[0]
                graphTime = to_graph[1]
                graphName = to_graph[2]
                self.graphMapper[graphName].cb_append_data_point(value, graphTime)
                queueDb.put([to_graph[0], to_graph[1], to_graph[2]])
            time.sleep(0.001)

class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        dbQueue = Queue()
        dataQueue = Queue()

        self.ble_handler = DreamBand.DreamBandHandler(dataQueue)
        self.db_connector = InfluxConnector.InfluxConnector(dbQueue)

        graphs = ["EOG","Accel X","Accel Y","Accel Z","Red Light","IR Light"]
        self.graph = GraphWidget(None, graphs)
        self.graph.show()

        dbProcess = Process(target=self.db_connector.start_listening)
        dbProcess.start()
        bleProcess = Process(target=self.ble_handler.async_thread_target)
        bleProcess.start()

        graphThread = Thread(target=self.graph.start_graphing, args=(dataQueue, dbQueue))
        graphThread.start()


def main():
    app = QtWidgets.QApplication(sys.argv)
    MainWidget()
    app.exec()
    print("Here")

if __name__ == "__main__":
    main()
