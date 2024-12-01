from typing import TYPE_CHECKING

from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.processing import execAlgorithmDialog
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface

import wurman_dots.resources  # noqa: F401
from wurman_dots.about_dialog import AboutDialog
from wurman_dots.processing import WurmanDotsAlgorithmProvider

if TYPE_CHECKING:
    assert isinstance(iface, QgisInterface)


class WurmanDotsPlugin:
    def __init__(self, _: QgisInterface):
        self.__provider = None
        self.__run_action = None
        self.__about_action = None

    def initProcessing(self):
        self.__provider = WurmanDotsAlgorithmProvider()
        QgsApplication.processingRegistry().addProvider(self.__provider)

    def initGui(self):
        self.initProcessing()

        menu_name = self.tr("&Wurman Dots")

        self.__run_action = QAction(
            QIcon(":/plugins/wurman_points/icons/wurman_dots_logo.svg"),
            self.tr("Create Wurman Dots"),
            iface.mainWindow(),
        )
        self.__run_action.triggered.connect(self.__exec_algorithm)
        iface.addPluginToVectorMenu(menu_name, self.__run_action)

        self.__about_action = QAction(
            self.tr("About plugin…"),
            iface.mainWindow(),
        )
        self.__about_action.triggered.connect(self.__open_about_dialog)
        iface.addPluginToVectorMenu(menu_name, self.__about_action)

        for action in iface.vectorMenu().actions():
            if action.text() != menu_name:
                continue
            action.setIcon(
                QIcon(":/plugins/wurman_points/icons/wurman_dots_logo.svg")
            )

        self.__show_help_action = QAction(
            QIcon(":/plugins/wurman_points/icons/wurman_dots_logo.svg"),
            "Wurman Points",
        )
        self.__show_help_action.triggered.connect(self.__open_about_dialog)
        plugin_help_menu = iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self.__show_help_action)

    def unload(self):
        iface.removePluginVectorMenu(
            self.tr("&Wurman Dots"), self.__run_action
        )
        iface.removePluginVectorMenu(
            self.tr("&Wurman Dots"), self.__about_action
        )
        QgsApplication.processingRegistry().removeProvider(self.__provider)

    def tr(self, string: str, context: str = "") -> str:
        if context == "":
            context = self.__class__.__name__
        return QgsApplication.translate(context, string)

    def __exec_algorithm(self):
        execAlgorithmDialog("wurman_dots:create_wurman_dots")

    def __open_about_dialog(self) -> None:
        dialog = AboutDialog("wurman_dots")
        dialog.exec()
