from PySide6 import QtCore, QtGui, QtWidgets
from multiprocessing import Process, Queue
import time
import datetime

"""
Event List:
InfluxPostDataEvent - The db connector sent data to the database
InfluxControlThreadStart - The db connector control thread has started


Command List:

InfluxControlStartPosting - The db connector started listening to db requests.
InfluxControlStopPosting - The db connector stopped listening to db requests.

"""

BAND_CONNECTED = "Connected."
BAND_DISCONNECTED = "Disconnected."

BAND_SAMPLING = "Currently Sampling."
BAND_NOT_SAMPLING = "Not Sampling."

THREAD_LISTENING = "Thread is listening."
THREAD_NOT_LISTENING = "Thread is not listening."

class DBControlWidget(QtWidgets.QWidget):
    def __init__(self,
                dbControlQueue:Queue=None):
        super().__init__()
        self.dbControlQueue = dbControlQueue
        self.setupUi()

    def setupUi(self):
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setupExecutionButtonsUi()
        self.mainLayout.addWidget(self.execButtonsWidget)

    def setupExecutionButtonsUi(self):

        # Button Widget
        self.execButtonsWidget = QtWidgets.QWidget()
        self.execButtonsWidgetLayout = QtWidgets.QVBoxLayout(self.execButtonsWidget)

        # Start Recording Button
        self.startPosting = QtWidgets.QPushButton("Start Posting")
        self.execButtonsWidgetLayout.addWidget(self.startPosting)
        self.startPosting.clicked.connect(self.startPostingButtonClicked)

        # Stop Recording Button
        self.stopPosting = QtWidgets.QPushButton("Stop Posting")
        self.execButtonsWidgetLayout.addWidget(self.stopPosting)
        self.stopPosting.clicked.connect(self.stopPostingButtonClicked)

    def startPostingButtonClicked(self):
        command = []
        commandText = "InfluxControlStartPosting"
        command.append(commandText)
        self.dbControlQueue.put(command)

    def stopPostingButtonClicked(self):
        command = []
        commandText = "InfluxControlStopPosting"
        command.append(commandText)
        self.dbControlQueue.put(command)

class DBStatsWidget(QtCore.QThread):
    updateSignal = QtCore.Signal(list)

    def __init__(self, dbEventQueue:Queue=None):
        super().__init__()
        self.mainWidget = QtWidgets.QWidget()
        self.dbEventQueue = dbEventQueue
        self.updateSignal.connect(self.updateUi)
        self.isListening = False
        self.setupUi()

    def setupStateUi(self):
        row = 0
        titleCol = 0
        valueCol = 1
        # DB Stats Widget
        self.dbStatsWidget = QtWidgets.QWidget()
        self.dbStatsWidgetLayout = QtWidgets.QGridLayout(self.dbStatsWidget)
        
        ## DB Post Counters
        ### DB Posts Sent
        self.dbPostCount = 0
        self.dbPostCounterWidgetTitle = QtWidgets.QLabel("DB Post Count: ")
        self.dbStatsWidgetLayout.addWidget(self.dbPostCounterWidgetTitle, row, titleCol)
        self.dbPostCounterWidget = QtWidgets.QLabel(str(self.dbPostCount))
        self.dbStatsWidgetLayout.addWidget(self.dbPostCounterWidget, row, valueCol)
        row +=1

        ### DB Errors
        self.dbErrorCounts = 0
        self.dbErrorCounterWidgetTitle = QtWidgets.QLabel("DB Errors: ")
        self.dbStatsWidgetLayout.addWidget(self.dbErrorCounterWidgetTitle, row, titleCol)
        self.dbErrorCounterWidget = QtWidgets.QLabel(str(self.dbErrorCounts))
        self.dbStatsWidgetLayout.addWidget(self.dbErrorCounterWidget, row, valueCol)
        row +=1

        ### Control Thread Listening
        self.controlThreadListening = False
        self.controlThreadListeningWidgetTitle = QtWidgets.QLabel("Control: ")
        self.dbStatsWidgetLayout.addWidget(self.controlThreadListeningWidgetTitle, row, titleCol)
        self.controlThreadListeningWidget = QtWidgets.QLabel(THREAD_NOT_LISTENING)
        self.dbStatsWidgetLayout.addWidget(self.controlThreadListeningWidget, row, valueCol)
        row +=1

        ### Posting Thread 
        self.postingThreadListening = False
        self.postingThreadListeningWidgetTitle = QtWidgets.QLabel("Posting: ")
        self.dbStatsWidgetLayout.addWidget(self.postingThreadListeningWidgetTitle, row, titleCol)
        self.postingThreadListeningWidget = QtWidgets.QLabel(THREAD_NOT_LISTENING)
        self.dbStatsWidgetLayout.addWidget(self.postingThreadListeningWidget, row, valueCol)
        row +=1

    def setupLogUi(self):
        self.dbLoggerWidget = QtWidgets.QTextBrowser()

    def setupUi(self):
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        
        self.setupStateUi()
        self.mainLayout.addWidget(self.dbStatsWidget)

        self.setupLogUi()
        self.mainLayout.addWidget(self.dbLoggerWidget)

    def formatLogString(self, logParts):
        log = ""
        local_dt = datetime.datetime.now()
        local_dt_est = local_dt + datetime.timedelta(hours=4)
        iso_format = local_dt_est.isoformat()
        logtime = iso_format
        logHeader = logParts[0]
        logDelimeter = " | "
        logDesc = logParts[1]
        log = logtime + logDelimeter + logHeader + logDelimeter + logDesc
        return log

    def updateUi(self, event):
        """
        Event List:
        InfluxPostDataEvent - The db connector sent data to the database
        InfluxControlThreadStart - The db connector control thread has started
        """
        isLogged = {
            "InfluxPostDataEvent": True,
            "InfluxControlThreadStart": True,
            "InfluxControlStartPosting": True,
            "InfluxControlStopPosting": True,
        }
        if(event[0] == "InfluxPostDataEvent"):
            self.dbPostCount += 1
            self.dbPostCounterWidget.setText(str(self.dbPostCount))
        elif(event[0] == "InfluxControlThreadStart"):
            self.controlThreadListening = True
            self.controlThreadListeningWidget.setText(THREAD_LISTENING)
        elif(event[0] == "InfluxControlStartPosting"):
            self.postingThreadListening = True
            self.postingThreadListeningWidget.setText(THREAD_LISTENING)
        elif(event[0] == "InfluxControlStopPosting"):
            self.postingThreadListening = False
            self.postingThreadListeningWidget.setText(THREAD_NOT_LISTENING)
        # If is logged, log it
        if(event[0] in isLogged):
            self.dbLoggerWidget.append(self.formatLogString(event))

    def listener(self):
        while(self.isListening):
            if(self.dbEventQueue.empty() == False):
                event = self.dbEventQueue.get()
                self.updateSignal.emit(event)
            time.sleep(0.01)

    def run(self):
        self.isListening = True
        self.listener()

    def die(self):
        self.isListening = False
