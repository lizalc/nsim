from PySide2.QtCore import QByteArray, QFile, QFileInfo, QTextStream, QTemporaryDir, QTemporaryFile
from resources.available import Resources

import base64

class ResourceManager:
    """
    NSim resource manager

    Handles all file I/O
    """

    def __init__(self):
        self.currentResourceName = None
        self.tmpDir = QTemporaryDir()
        self.tmpFiles = []

    @property
    def pennSim(self):
        try:
            return self._pennSim
        except AttributeError:
            self._pennSim = self.createTemporaryFromResource(Resources.PennSim.value)
            return self._pennSim

    @pennSim.setter
    def pennSim(self, value):
        self._pennSim = value

    # Would prefer to not open / close files each time. Keep around unless other resource is needed.
    def getContents(self, requested):
        resource = QFile(requested)

        if not resource.open(QFile.ReadOnly):
            raise Exception('Unable to open resource: {}'.format(requested))

        # QTextStream allows for easier handling of encoding / locale
        resourceStream = QTextStream(resource)
        contents = resourceStream.readAll()

        if resourceStream.status() != QTextStream.Ok:
            raise Exception('ERROR: Issue reading resource contents: {}'.format(requested))

        return contents

    def saveContents(self, requested, contents):
        resource = QFile(requested)

        if not resource.open(QFile.WriteOnly):
            raise Exception('Unable to open resource: {}'.format(requested))

        resourceStream = QTextStream(resource)
        resourceStream << contents

        if resourceStream.status() != QTextStream.Ok:
            raise Exception('ERROR: Issue writing resource contents: {}'.format(requested))

    def createTemporaryFromResource(self, requested):
        temporary = QTemporaryFile.createNativeFile(requested.absoluteFilePath())
        if not temporary:
            raise Exception('Unable to create temporary file: {}'.format(requested.baseName()))

        newPath = temporary.fileName().replace('/tmp/', '{}/'.format(self.tmpDir.path()))
        if not temporary.rename(newPath):
            # If file could not be moved to tmpDir, need to keep track of it so the program can
            # clean it up on exit. Otherwise it will be left on disk.
            self.tmpFiles.append(temporary)

        return QFileInfo(temporary)

    def createTemporaryFromContents(self, contents):
        temporary = QTemporaryFile('{}/script'.format(self.tmpDir.path()))
        temporary.setAutoRemove(False)

        if not temporary.open():
            raise Exception('Unable to create temporary file')

        temp = QByteArray.fromBase64(base64.b64encode(contents.encode()))

        temporary.write(temp)
        temporary.close()

        return QFileInfo(temporary)

    def createLocalFromContents(self, contents, workingDir, name='nsim.pm'):
        resource = QFile('{}/{}'.format(workingDir.absoluteFilePath(), name))

        if not resource.open(QFile.WriteOnly):
            raise Exception('ERROR: Could not create script file.')

        resourceStream = QTextStream(resource)
        resourceStream << contents

        if resourceStream.status() != QTextStream.Ok:
            raise Exception('ERROR: Issue writing script file')

        return resource

    def createLocalOS(self, requested, workingDir):
        resource_obj = self.createLocalFromResource(requested.absoluteFilePath(), workingDir)
        resource_sym = self.createLocalFromResource(requested.absoluteFilePath().replace('.obj', '.sym'), workingDir)

        return [resource_obj, resource_sym]

    def createLocalFromResource(self, requested, workingDir):
        requestedInfo = QFileInfo('{}/{}'.format(workingDir.absoluteFilePath(), requested.replace(':/', '')))

        if requestedInfo.exists():
            return QFile(requestedInfo.absoluteFilePath())

        resource = QFile(requested)
        resource.copy(requestedInfo.absoluteFilePath())
        if resource.isOpen():
            resource.close()
        resource.setFileName(requestedInfo.absoluteFilePath())

        if not resource.exists():
            raise Exception('ERROR: Could not create / locate file: {}'.format(requestedInfo.absoluteFilePath()))

        return resource

    def __del__(self):
        for tmpFile in self.tmpFiles:
            tmpFile.remove()
