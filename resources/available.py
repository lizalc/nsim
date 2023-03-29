from PySide2.QtCore import QFileInfo
from enum import Enum
import resources.generated


class Resources(Enum):
    '''
    Defines available resources it Qt5 Resource system

    Currently all resources are available in nsim.rcc and that is not expected to
    change. However, if it does, new resources can be registered here (as well as
    the .qrc) by defining the appropriate property.

    Using bare resource strings in the code is discouraged.

    Special Notes:
    The operating system resources define both .obj and .sym files. Rather than
    defining the .obj and .sym separately the .sym is implicitly loaded from the
    same location as the .obj.
    This may change.
    '''

    PennSim = QFileInfo(':/PennSim.jar')
    LC3 = QFileInfo(':/lc3os.obj')
    P2 = QFileInfo(':/p2os.obj')
    P3 = QFileInfo(':/p3os.obj')
    DefaultTest = QFileInfo(':/default_test.pm')
    AssemblyTest = QFileInfo(':/assembly_test.pm')
