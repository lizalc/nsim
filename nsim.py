import os, sys

from PySide2.QtCore import QObject, Slot, Signal, QStandardPaths, QFileInfo, QProcess, QTextStream, QTimer
from PySide2.QtWidgets import QApplication, QMessageBox

from resources.manager import ResourceManager
from resources.available import Resources
from ui.nmainwindow import NSimMainWindow

import resources.generated


class NSim(QObject):
    pennSimScript_started = Signal()
    pennSimScript_finished = Signal()
    pennSimScript_output = Signal(str)
    pennSim_finished = Signal()

    def __init__(self):
        super(NSim, self).__init__()
        self.setObjectName('NSim')

        # Establish ResourceManager, shared with mainWindow
        self.resources = ResourceManager()

        # NSimMainWindow can emit signals connected to slots in NSim and vice-versa
        self.mainWindow = NSimMainWindow(self.resources)
        self.mainWindow.runPennSim.connect(self.pennSimScript)
        self.mainWindow.runPennSimAll.connect(self.pennSimScriptAll)
        self.mainWindow.runPennSim[QFileInfo].connect(self.pennSim)
        self.mainWindow.show()

        # Place this in a QThread that's not started till runButton clicked? Then can terminate QThread
        # to stop processing all files when runAll is checked
        self.pennSimScript_started.connect(self.mainWindow.pennSimScript_started)
        self.pennSimScript_finished.connect(self.mainWindow.pennSimScript_finished)
        self.pennSimScript_output.connect(self.mainWindow.pennSimScript_output)
        self.pennSim_finished.connect(self.mainWindow.pennSim_finished)

        self.javaBin = QStandardPaths.findExecutable('java')
        if not self.javaBin:
            QMessageBox.warning(self.mainWindow, 'Java Not Found', 'Could not find java in PATH. Please set manually.')
        if not self.resources.tmpDir.isValid():
            QMessageBox.warning(self.mainWindow, 'Temporary Directory Unavailable',
                                'Could not create temporary directory')

    @Slot(QFileInfo, QFileInfo, str, bool)
    def pennSimScript(self, workingDir, pennSimOS, script, cliMode):
        self.scriptProcess = QProcess(self)
        self.scriptProcess.setWorkingDirectory(workingDir.absoluteFilePath())
        self.scriptProcess.workingFiles = []
        self.scriptProcess.workingFiles.extend(self.resources.createLocalOS(pennSimOS, workingDir))
        self.scriptProcess.workingFiles.append(self.resources.createLocalFromContents(script, workingDir))

        args = ['-jar', self.resources.pennSim.absoluteFilePath(), '-s',
                self.resources.createTemporaryFromContents(script).absoluteFilePath()]

        if cliMode:
            args.append('-t')
            # Start a 30 second timer before terminating the process. Should really be adjustable
            QTimer.singleShot(30000, self.pennSimScriptProcess_terminated)
        self.scriptProcess.setArguments(args)
        self.scriptProcess.started.connect(self.pennSimScriptProcess_started)
        self.scriptProcess.finished.connect(self.pennSimScriptProcess_finished)
        self.startPennSim(self.scriptProcess)

    @Slot(str, QFileInfo, str, str, bool)
    def pennSimScriptAll(self, rootDir, pennSimOS, script, programName, cliMode):
        workingDirs = self.buildDirs(rootDir, set(rootDir))
        for workingDir in workingDirs:
            if os.path.exists(os.path.join(workingDir, programName)):
                self.pennSimScript(QFileInfo(workingDir), pennSimOS, script, cliMode)
                self.scriptProcess.waitForFinished(-1)

    # Should really use QDirIterator to be consistent.
    def buildDirs(self, rootDir, val=set()):
        with os.scandir(rootDir) as startDir:
            for testDir in startDir:
                if testDir.is_dir():
                    val.add(testDir.path)
                    self.buildDirs(testDir, val)
        return sorted(val)

    @Slot(QFileInfo)
    def pennSim(self, workingDir):
        self.pennSimProcess = QProcess(self)
        self.pennSimProcess.setWorkingDirectory(workingDir.absoluteFilePath())
        self.pennSimProcess.setArguments(['-jar', self.resources.pennSim.absoluteFilePath()])

        self.pennSimProcess.workingFiles = []
        # Provide all OS files
        for resource in Resources:
            if resource is Resources.LC3 or resource is Resources.P2 or resource is Resources.P3:
                self.pennSimProcess.workingFiles.extend(self.resources.createLocalOS(resource.value, workingDir))

        self.pennSimProcess.finished.connect(self.pennSimProcess_finished)
        self.startPennSim(self.pennSimProcess)

    def startPennSim(self, process):
        process.setProgram(self.javaBin)
        process.start()

    @Slot()
    def pennSimScriptProcess_started(self):
        self.pennSimScript_started.emit()

    @Slot(int, QProcess.ExitStatus)
    def pennSimScriptProcess_finished(self, retVal, status):
        for file in self.scriptProcess.workingFiles:
            file.remove()
        if '-t' in self.scriptProcess.arguments():
            cliOutput = 'Results for: {}\n'.format(self.scriptProcess.workingDirectory())
            rawProcessOutput = self.scriptProcess.readAll()
            rawProcessOutputStream = QTextStream(rawProcessOutput)
            rawOutput = rawProcessOutputStream.readAll()
            # Strip PennSim's common 'header' / 'footer' output to save space.
            rawOutput = rawOutput[rawOutput.find('==>'):rawOutput.find('Bye!')]
            cliOutput += rawOutput
            self.pennSimScript_output.emit(cliOutput)
        self.pennSimScript_finished.emit()

    @Slot()
    def pennSimScriptProcess_terminated(self):
        if self.scriptProcess.state() is not QProcess.NotRunning:
            self.pennSimScript_output.emit('Terminated (timeout): {}'.format(self.scriptProcess.workingDirectory()))
            self.scriptProcess.terminate()

    @Slot(int, QProcess.ExitStatus)
    def pennSimProcess_finished(self, retVal, status):
        for file in self.pennSimProcess.workingFiles:
            file.remove()
        self.pennSim_finished.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('NSim')
    nsim = NSim()
    sys.exit(app.exec_())
