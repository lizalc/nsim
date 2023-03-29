from PySide2.QtCore import QFileInfo, QModelIndex, Signal, Slot, QStandardPaths
from PySide2.QtWidgets import QFileDialog, QFileSystemModel, QMainWindow, QMessageBox

from resources.available import Resources
from ui.nsim_rc import Ui_MainWindow

import re


class NSimMainWindow(QMainWindow):
    # Signal for running PennSim.
    # 1 - Passes current working dir, selected OS, and script contents.
    # 2 - Passes current working dir only
    runPennSim = Signal((QFileInfo, QFileInfo, str, bool), (QFileInfo,))

    # Signal for running PennSim when runAll is checked
    # Add programName otherwise the same as above->1
    runPennSimAll = Signal(str, QFileInfo, str, str, bool)

    def __init__(self, _resourceManager):
        super(NSimMainWindow, self).__init__()

        self.resources = _resourceManager

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.pennSimGroupBox.hide()
        # Currently workingDirLabel is a member of pennSimGroupBox since Qt Designer
        # doesn't allow adding widgets to statusBars. It's already defined otherwise
        # could just create it manually.
        self.statusBar().addWidget(self.ui.workingDirLabel)
        self.setUnifiedTitleAndToolBarOnMac(True)

    @property
    def currentWorkingDir(self):
        try:
            return self._currentWorkingDir
        except AttributeError:
            self.currentWorkingDir = QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0]
            self.openDir(self.currentWorkingDir.absoluteFilePath())
            return self._currentWorkingDir

    @currentWorkingDir.setter
    def currentWorkingDir(self, value):
        self._currentWorkingDir = QFileInfo(value)
        self.ui.workingDirLabel.setText('Working Directory: {}'.format(value))

    @property
    def selectedOS(self):
        try:
            return self._selectedOS
        except AttributeError:
            self._selectedOS = Resources.LC3.value
            return self._selectedOS

    @selectedOS.setter
    def selectedOS(self, value):
        self._selectedOS = value

    @property
    def programName(self):
        try:
            return self._programName
        except AttributeError:
            return '{asm}'

    @programName.setter
    def programName(self, value):
        self._programName = value
        self.ui.programNameEdit.setText(value)

    ## Root Directory

    @Slot()
    def on_actionOpen_Dir_triggered(self):
        dirPath = QFileDialog.getExistingDirectory(self)
        self.openDir(dirPath)

    @Slot()
    def on_openDirButton_clicked(self):
        dirPath = QFileDialog.getExistingDirectory(self)
        self.openDir(dirPath)

    # Sometimes it might appear that the treeView isn't updated when selecting another directory.
    # This is due to the system file picker appearing to select a different directory but instead
    # keeping the current directory selected (especially noticeable on GNOME)
    def openDir(self, dirPath):
        # Only change anything if directory was selected
        if dirPath:
            self.setup_treeview(dirPath)
            self.currentWorkingDir = dirPath
            self.ui.dirView.setTitle('Root: {}'.format(self.currentWorkingDir.completeBaseName()))
            self.ui.runPennSimButton.setEnabled(True)

    def setup_treeview(self, dirPath):
        # Initialize fsModel only once
        try:
            self.ui.dirTreeView.setRootIndex(self.fsModel.setRootPath(dirPath))
        except AttributeError:
            self.fsModel = QFileSystemModel()
            # self.fsModel.setReadOnly(True)
            self.ui.dirTreeView.setModel(self.fsModel)
            self.ui.dirTreeView.setRootIndex(self.fsModel.setRootPath(dirPath))
            for column in range(1, self.fsModel.columnCount()):
                self.ui.dirTreeView.hideColumn(column)

    ## END Root Directory

    ## Treeview Navigation

    # XXX - Won't distinguish between navigating through directorys via clicks and actually intending to select a directory
    @Slot(QModelIndex)
    def on_dirTreeView_clicked(self, index):
        selection = index.model().fileInfo(index)
        if selection.isDir():
            self.currentWorkingDir = selection.absoluteFilePath()

    @Slot(QModelIndex)
    def on_dirTreeView_activated(self, index):
        selected_file = index.model().fileInfo(index)
        if selected_file.isFile():
            if selected_file.suffix() in ['pm', 'sc', 'sr', 'scr']:
                self.loadScript(selected_file.absoluteFilePath())
                # Reasonable to assume script contains relative paths
                self.currentWorkingDir = selected_file.absolutePath()
            if selected_file.suffix() == 'asm':
                self.programName = selected_file.fileName()
                self.currentWorkingDir = selected_file.absolutePath()

    ## END Treeview Navigation

    ## Program Name Edit

    @Slot()
    def on_programNameEdit_editingFinished(self):
        programName = self.ui.programNameEdit.text()
        if programName:
            if '.asm' not in programName:
                programName += '.asm'
                # Ensure no duplicate periods were added
                self.programName = re.sub("(?P<char>[" + re.escape('.') + "])(?P=char)+", r'\1', programName)

    ## END Program Name Edit

    ## Script Combo Box

    @Slot(str)
    def on_scriptComboBox_activated(self, selection):
        resource = None
        if selection == 'Default':
            resource = Resources.DefaultTest.value
            self.ui.scriptGroupBox.setTitle('Script: Default')
        if selection == 'Assembly Test':
            resource = Resources.AssemblyTest.value
            self.ui.scriptGroupBox.setTitle('Script: Assembly Test')
        if resource:
            self.checkScriptSave()
            self.setScriptEditContents(self.resources.getContents(resource.absoluteFilePath()))
            self.ui.saveAsScriptButton.setEnabled(False)

    ## END Script Combo Box

    ## OS Combo Box

    @Slot(str)
    def on_osComboBox_activated(self, selection):
        resource = None
        if selection == 'lc3os':
            resource = Resources.LC3.value
        if selection == 'p2os':
            resource = Resources.P2.value
        if selection == 'p3os':
            resource = Resources.P3.value
        if selection == 'Other...':
            resource, _ = QFileDialog.getOpenFileName(self, caption='Select OS (obj or asm)',
                                                      filter='OBJ(*.obj);;ASM (*.asm)')
            resource = QFileInfo(resource)

        if resource:
            self.selectedOS = resource

    ## END OS Combo Box

    ## Script Editor

    # For setting the editor contents, as long as the keys in a particular format string are all defined
    # the format will not throw an error. Meaning additional keys not used in the format string are just
    # ignored. This means formatting can be performed on *any* input which makes formatting the default
    # and assembly scripts easier.
    def setScriptEditContents(self, contents):
        self.ui.scriptEdit.setPlainText(contents.format(os=self.selectedOS.fileName(), asm=self.programName,
                                                        obj=self.programName.replace('.asm', '.obj')))

    @Slot()
    def on_scriptEdit_textChanged(self):
        enabled = True if self.ui.scriptEdit.toPlainText() else False
        self.ui.saveAsScriptButton.setEnabled(enabled)
        self.ui.allTestsCheckBox.setEnabled(enabled)
        self.ui.cliModeCheckBox.setEnabled(enabled)
        self.ui.runButton.setEnabled(enabled)

    @Slot(bool)
    def on_scriptEdit_modificationChanged(self, status):
        self.ui.scriptEdit.setWindowModified(status)

    @Slot(str)
    def pennSimScript_output(self, output):
        self.ui.actionShow_PennSimCLIOutput.setChecked(True)
        self.ui.pennSimTextBrowser.append(output)

    ## END Script Editor

    ## Script Loading

    @Slot()
    def on_loadScriptButton_clicked(self):
        scriptPath, _ = QFileDialog.getOpenFileName(self, caption='Open Script',
                                                    filter='PennSim Script (*.pm *.sc *.sr *.scr)')
        self.loadScript(scriptPath)

    def loadScript(self, scriptPath):
        if scriptPath:
            try:
                self.setScriptEditContents(self.resources.getContents(scriptPath))
                self.currentWorkingDir = QFileInfo(scriptPath).absolutePath()
            except Exception as e:
                QMessageBox.warning(self, 'Load Error', e.args[0])

    ## END Script Loading

    ## Script Save As

    @Slot()
    def on_saveAsScriptButton_clicked(self):
        scriptPath, _ = QFileDialog.getSaveFileName(self, 'Save Script', 'script.pm',
                                                    filter='PennSim Script (*.pm *.sc *.sr *.scr)')
        self.saveScript(scriptPath)

    def saveScript(self, scriptPath):
        if scriptPath:
            try:
                self.resources.saveContents(scriptPath, self.ui.scriptEdit.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, 'Save Error', e.args[0])

            self.ui.statusbar.showMessage('{} written.'.format(scriptPath), 2000)

    ## END Script Save A

    ## Run PennSim
    @Slot()
    def on_runPennSimButton_clicked(self):
        self.ui.runPennSimButton.setEnabled(False)
        self.runPennSim[QFileInfo].emit(self.currentWorkingDir)

    @Slot()
    def pennSim_finished(self):
        self.ui.runPennSimButton.setEnabled(True)

    @Slot()
    def on_runButton_clicked(self):
        if not self.ui.allTestsCheckBox.isChecked():
            self.runPennSim.emit(self.currentWorkingDir, self.selectedOS, self.ui.scriptEdit.toPlainText(),
                                 self.ui.cliModeCheckBox.isChecked())
        else:
            if self.ui.programNameEdit.text():
                checkContinue = QMessageBox.warning(self, 'Run All',
                                                    'Warning: Testing against all files may take a long time and cause '
                                                    'the window to appear to freeze. There is currently no method to '
                                                    'cancel.\n\nContinue?',
                                                    QMessageBox.No | QMessageBox.Yes, QMessageBox.No)
                if checkContinue == QMessageBox.Yes:
                    try:
                        self.runPennSimAll.emit(self.fsModel.rootDirectory().absolutePath(), self.selectedOS,
                                                self.ui.scriptEdit.toPlainText(), self.programName,
                                                self.ui.cliModeCheckBox.isChecked())
                    except AttributeError:
                        # Use working directory in no root defined
                        self.runPennSimAll.emit(self.currentWorkingDir.absoluteFilePath(), self.selectedOS,
                                                self.ui.scriptEdit.toPlainText(), self.programName,
                                                self.ui.cliModeCheckBox.isChecked())
            else:
                QMessageBox.warning(self, 'No Program Name',
                                    'Please define a program name to run a script against all files.')

    @Slot()
    def pennSimScript_started(self):
        self.ui.runButton.setEnabled(False)

    @Slot()
    def pennSimScript_finished(self):
        self.ui.runButton.setEnabled(True)

    ## END Run PennSim

    ## PennSim CLI Output

    @Slot(bool)
    def on_pennSimGroupBox_toggled(self, checked):
        if not checked:
            self.ui.actionShow_PennSimCLIOutput.setChecked(False)

    @Slot(bool)
    def on_actionShow_PennSimCLIOutput_toggled(self, checked):
        if checked:
            self.ui.pennSimGroupBox.show()
            self.ui.pennSimGroupBox.setChecked(True)
        else:
            self.ui.pennSimGroupBox.hide()

    @Slot()
    def on_clearCLIOutputButton_clicked(self):
        self.ui.pennSimTextBrowser.clear()

    ## END PennSim CLI Output

    ## Program Exit

    def closeEvent(self, *args, **kwargs):
        self.checkScriptSave('Save script before exit?')
        args[0].accept()

    def checkScriptSave(self, prompt='Save unsaved changes?'):
        # if self.ui.saveAsScriptButton.isEnabled():
        if self.ui.scriptEdit.isWindowModified():
            checkQuit = QMessageBox.question(self, 'Unsaved Script', prompt,
                                             QMessageBox.No | QMessageBox.Yes, QMessageBox.Yes)
            if checkQuit == QMessageBox.Yes:
                self.ui.saveAsScriptButton.clicked.emit()

    ## END Program Exit
