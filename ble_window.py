from PySide6 import QtCore, QtGui, QtWidgets
from multiprocessing import Process, Queue
import datetime
import time

"""
Event List:

BleWrite - Band manager did a GATT write
BleRead - Band manager did a GATT read

BleControlThreadStart - Band manager proccess thread started
BleDisconnectedEvent - Band was disconnected
BleConnectionEvent - Band BLE connection was established
BleToggleSamplingEvent - Band sampling was toggled on or off (off at start) 

BleInvalidRequest - Band manager had an invalid request
BleErrorCode - Band returned an error code
BleConnectionError - Band could not connect 


Command List:

BleControlConnect - Tell band manager to connect to band
BleControlDisconnect - Tell band manager to disconnect from band

BleControlStopRecording - Tell band manager to stop recording session
BleControlStartRecording - Tell band manager to start recording session 


"""

BAND_CONNECTED = "Connected."
BAND_DISCONNECTED = "Disconnected."

BAND_SAMPLING = "Currently Sampling."
BAND_NOT_SAMPLING = "Not Sampling."

THREAD_LISTENING = "Thread is listening."
THREAD_NOT_LISTENING = "Thread is not listening."

class BLEControlWidget(QtWidgets.QWidget):
    def __init__(self,
                bleControlQueue:Queue=None):
        super().__init__()
        self.bleControlQueue = bleControlQueue
        self.setupUi()

    def setupUi(self):
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setupRawCommandWindow()
        self.mainLayout.addWidget(self.rawCommandWidget)
        self.setupExecutionButtonsUi()
        self.mainLayout.addWidget(self.execButtonsWidget)

    def setupRawCommandWindow(self):
        self.rawCommandWidget = QtWidgets.QWidget()
        self.rawCommandWidgetLayout = QtWidgets.QGridLayout(self.rawCommandWidget)
        self.rawCommandWidgetTitle = QtWidgets.QLabel("Send A Raw Command")
        self.rawCommandWidgetLayout.addWidget(self.rawCommandWidgetTitle, 0, 0, 1, 1)
        self.rawCommandTextBox = QtWidgets.QLineEdit()
        self.rawCommandWidgetLayout.addWidget(self.rawCommandTextBox, 1, 0, 1, 3)

        self.rawCommandSendButton = QtWidgets.QPushButton("Send")
        self.rawCommandWidgetLayout.addWidget(self.rawCommandSendButton, 1, 3, 1, 1)
        self.rawCommandSendButton.clicked.connect(self.rawCommandSendButtonClicked)

    def rawCommandSendButtonClicked(self):
        # Get Text
        command = []
        commandText = self.rawCommandTextBox.text()
        command.append(commandText)
        self.bleControlQueue.put(command)
        self.rawCommandTextBox.setText("")

    def setupExecutionButtonsUi(self):

        # Button Widget
        self.execButtonsWidget = QtWidgets.QWidget()
        self.execButtonsWidgetLayout = QtWidgets.QVBoxLayout(self.execButtonsWidget)
        
        # Connection Button
        self.connectButton = QtWidgets.QPushButton("Connect")
        self.execButtonsWidgetLayout.addWidget(self.connectButton)
        self.connectButton.clicked.connect(self.connectButtonClicked)
        
        # Disconnection Button
        self.disconnectButton = QtWidgets.QPushButton("Disconnect")
        self.execButtonsWidgetLayout.addWidget(self.disconnectButton)
        self.disconnectButton.clicked.connect(self.disconnectButtonClicked)

        # Start Recording Button
        self.startRecordingButton = QtWidgets.QPushButton("Start Recording")
        self.execButtonsWidgetLayout.addWidget(self.startRecordingButton)
        self.startRecordingButton.clicked.connect(self.startRecordingButtonClicked)

        # Stop Recording Button
        self.stopRecordingButton = QtWidgets.QPushButton("Stop Recording")
        self.execButtonsWidgetLayout.addWidget(self.stopRecordingButton)
        self.stopRecordingButton.clicked.connect(self.stopRecordingButtonClicked)

    def connectButtonClicked(self):
        command = []
        commandText = "BleControlConnect"
        command.append(commandText)
        self.bleControlQueue.put(command)

    def disconnectButtonClicked(self):
        command = []
        commandText = "BleControlDisconnect"
        command.append(commandText)
        self.bleControlQueue.put(command)


    def startRecordingButtonClicked(self):
        command = []
        commandText = "BleControlStartRecording"
        command.append(commandText)
        self.bleControlQueue.put(command)


    def stopRecordingButtonClicked(self):
        command = []
        commandText = "BleControlStopRecording"
        command.append(commandText)
        self.bleControlQueue.put(command)

class BLEStatsWidget(QtCore.QThread):
    updateSignal = QtCore.Signal(list)

    def __init__(self, bleEventQueue:Queue=None):
        super().__init__()
        self.mainWidget = QtWidgets.QWidget()
        self.bleEventQueue = bleEventQueue
        self.isListening = False
        self.updateSignal.connect(self.updateUi)
        self.setupUi()

    def setupStateUi(self):
        row = 0
        titleCol = 0
        valueCol = 1
        # Band State Widget
        self.stateWidget = QtWidgets.QWidget()
        self.stateLayout = QtWidgets.QGridLayout(self.stateWidget)
        ## Band State
        
        ### Control Thread Listening
        self.controlThreadListening = False
        self.controlThreadListeningWidgetTitle = QtWidgets.QLabel("Control: ")
        self.stateLayout.addWidget(self.controlThreadListeningWidgetTitle, row, titleCol)
        self.controlThreadListeningWidget = QtWidgets.QLabel(THREAD_NOT_LISTENING)
        self.stateLayout.addWidget(self.controlThreadListeningWidget, row, valueCol)
        row +=1

        ### Band Connected
        self.bandConnected = False
        self.bandConnectedWidgetTitle = QtWidgets.QLabel("Band Connection: ")
        self.stateLayout.addWidget(self.bandConnectedWidgetTitle, row, titleCol)
        self.bandConnectedWidget = QtWidgets.QLabel(BAND_DISCONNECTED)
        self.stateLayout.addWidget(self.bandConnectedWidget, row, valueCol)
        row +=1

        ### Band Sampling
        self.bandSamplingState = False
        self.bandSamplingStateWidgetTitle = QtWidgets.QLabel("Band Sampling: ")
        self.stateLayout.addWidget(self.bandSamplingStateWidgetTitle, row, titleCol)
        self.bandSamplingStateWidget = QtWidgets.QLabel(BAND_NOT_SAMPLING)
        self.stateLayout.addWidget(self.bandSamplingStateWidget, row, valueCol)
        row +=1
        
        ## Packet Counters
        ### Packets Sent
        self.packetSentCount = 0
        self.packetSentCounterWidgetTitle = QtWidgets.QLabel("BLE Packets Sent: ")
        self.stateLayout.addWidget(self.packetSentCounterWidgetTitle, row, titleCol)
        self.packetSentCounterWidget = QtWidgets.QLabel(str(self.packetSentCount))
        self.stateLayout.addWidget(self.packetSentCounterWidget, row, valueCol)
        row +=1

        ### Packets Received
        self.packetReceivedCount = 0
        self.packetRecievedCounterWidgetTitle = QtWidgets.QLabel("BLE Packets Received: ")
        self.stateLayout.addWidget(self.packetRecievedCounterWidgetTitle, row, titleCol)
        self.packetReceivedCounterWidget = QtWidgets.QLabel(str(self.packetReceivedCount))
        self.stateLayout.addWidget(self.packetReceivedCounterWidget, row, valueCol)
        row +=1

        ### BLE Errors
        self.bleErrorCounts = 0
        self.bleErrorCounterWidgetTitle = QtWidgets.QLabel("BLE Errors: ")
        self.stateLayout.addWidget(self.bleErrorCounterWidgetTitle, row, titleCol)
        self.bleErrorCounterWidget = QtWidgets.QLabel(str(self.bleErrorCounts))
        self.stateLayout.addWidget(self.bleErrorCounterWidget, row, valueCol)
        row +=1

    def setupLogUi(self):
        self.bandLoggerWidget = QtWidgets.QTextBrowser()

    def setupUi(self):
        self.mainLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        
        self.setupStateUi()
        self.mainLayout.addWidget(self.stateWidget)

        self.setupLogUi()
        self.mainLayout.addWidget(self.bandLoggerWidget)

    @QtCore.Slot(list)
    def updateUi(self, event):
        """
        Event List:

        BleWrite - Band manager did a GATT write
        BleRead - Band manager did a GATT read

        BleControlThreadStart - Band manager proccess thread started
        BleDisconnectedEvent - Band was disconnected
        BleConnectionEvent - Band BLE connection was established
        BleToggleSamplingEvent - Band sampling was toggled on or off (off at start) 

        BleInvalidRequest - Band manager had an invalid request
        BleErrorCode - Band returned an error code
        BleConnectionError - Band could not connect 
        """
        isLogged = {
            "BleWrite": True,
            "BleRead": True,

            "BleControlThreadStart": True,
            "BleDisconnectedEvent": True,
            "BleConnectionEvent": True,
            "BleToggleSamplingEvent": True,

            "BleInvalidRequest": True,
            "BleErrorCode": True,
            "BleConnectionError": True,
        }
        if(event[0] == "BleWrite"):
            self.packetSentCount += 1
            self.packetSentCounterWidget.setText((str(self.packetSentCount)))
        elif(event[0] == "BleRead"):
            self.packetReceivedCount += 1
            self.packetReceivedCounterWidget.setText(str(self.packetReceivedCount))
        elif(event[0] == "BleControlThreadStart"):
            self.controlThreadListening = True
            self.controlThreadListeningWidget.setText((THREAD_LISTENING))
        elif(event[0] == "BleDisconnectedEvent"):
            self.bandConnected = False
            self.bandConnectedWidget.setText((BAND_DISCONNECTED))
        elif(event[0] == "BleConnectionEvent"):
            self.bandConnected = True
            self.bandConnectedWidget.setText((BAND_CONNECTED))
        elif(event[0] == "BleToggleSamplingEvent"):
            if(self.bandSamplingState == True):
                    self.bandSamplingState = False
                    self.bandSamplingStateWidget.setText((BAND_NOT_SAMPLING))
            elif(self.bandSamplingState == False):
                    self.bandSamplingState = True
                    self.bandSamplingStateWidget.setText((BAND_SAMPLING))
        elif(event[0] == "BleInvalidRequest"):
            self.bleErrorCounts += 1
            self.bleErrorCounterWidget.setText(str(self.bleErrorCounts))
        elif(event[0] == "BleErrorCode"):
            self.bleErrorCounts += 1
            self.bleErrorCounterWidget.setText(str(self.bleErrorCounts))
        elif(event[0] == "BleConnectionError"):
            self.bleErrorCounts += 1
            self.bleErrorCounterWidget.setText(str(self.bleErrorCounts))

        # If is logged, log it
        if(event[0] in isLogged):
            self.bandLoggerWidget.append(self.formatLogString(event))

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

    def run(self):
        self.isListening = True
        self.listener()

    def die(self):
        self.isListening = False

    def listener(self):
        while(self.isListening):
            if(self.bleEventQueue.empty() == False):
                event = self.bleEventQueue.get()
                self.updateSignal.emit(event)
            time.sleep(0.01)
