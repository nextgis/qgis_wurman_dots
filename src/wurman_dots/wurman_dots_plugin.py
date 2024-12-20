from pathlib import Path
from typing import TYPE_CHECKING

from processing import execAlgorithmDialog
from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QFileInfo,
    QLocale,
    QSettings,
    QTranslator,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface

import wurman_dots.resources  # noqa: F401
from wurman_dots.about_dialog import AboutDialog
from wurman_dots.processing import WurmanDotsAlgorithmProvider

if TYPE_CHECKING:
    assert isinstance(iface, QgisInterface)

_current_path = str(Path(__file__).parent)


class WurmanDotsPlugin:
    def __init__(self, _: QgisInterface):
        self.__provider = None
        self.__algorithm_for_cell_size = None
        self.__algorithm_for_cell_count = None
        self.__about_action = None

        override_locale = QSettings().value(
            "locale/overrideFlag", False, type=bool
        )
        if not override_locale:
            locale_full_name = QLocale.system().name()
        else:
            locale_full_name = QSettings().value(
                "locale/userLocale", "", type=str
            )

        self.locale_path = (
            f"{_current_path}/i18n/wurman_dots_{locale_full_name[0:2]}.qm"
        )
        if QFileInfo(self.locale_path).exists():
            self.translator = QTranslator()
            self.translator.load(self.locale_path)
            QCoreApplication.installTranslator(self.translator)

    def initProcessing(self):
        self.__provider = WurmanDotsAlgorithmProvider()
        QgsApplication.processingRegistry().addProvider(self.__provider)

    def initGui(self):
        self.initProcessing()

        menu_name = self.tr("&Wurman Dots")

        self.__algorithm_for_cell_size = QAction(
            QIcon(":/plugins/wurman_dots/icons/wurman_dots_logo.svg"),
            self.tr("Create Wurman Dots (grid based on cell size)"),
            iface.mainWindow(),
        )
        self.__algorithm_for_cell_size.triggered.connect(
            self.__exec_algorithm_for_cell_size
        )
        iface.addPluginToVectorMenu(menu_name, self.__algorithm_for_cell_size)

        self.__algorithm_for_cell_count = QAction(
            QIcon(":/plugins/wurman_dots/icons/wurman_dots_logo.svg"),
            self.tr("Create Wurman Dots (grid based on cell count)"),
            iface.mainWindow(),
        )
        self.__algorithm_for_cell_count.triggered.connect(
            self.__exec_algorithm_for_cell_count
        )
        iface.addPluginToVectorMenu(menu_name, self.__algorithm_for_cell_count)

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
                QIcon(":/plugins/wurman_dots/icons/wurman_dots_logo.svg")
            )

        self.__show_help_action = QAction(
            QIcon(":/plugins/wurman_dots/icons/wurman_dots_logo.svg"),
            "Wurman Dots",
        )
        self.__show_help_action.triggered.connect(self.__open_about_dialog)
        plugin_help_menu = iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self.__show_help_action)

    def unload(self):
        iface.removePluginVectorMenu(
            self.tr("&Wurman Dots"), self.__algorithm_for_cell_size
        )
        iface.removePluginVectorMenu(
            self.tr("&Wurman Dots"), self.__algorithm_for_cell_count
        )
        iface.removePluginVectorMenu(
            self.tr("&Wurman Dots"), self.__about_action
        )
        QgsApplication.processingRegistry().removeProvider(self.__provider)

    def tr(self, string: str, context: str = "") -> str:
        if context == "":
            context = self.__class__.__name__
        return QgsApplication.translate(context, string)

    def __exec_algorithm_for_cell_size(self):
        execAlgorithmDialog(
            "wurman_dots:create_wurman_dots_based_on_cell_size"
        )

    def __exec_algorithm_for_cell_count(self):
        execAlgorithmDialog(
            "wurman_dots:create_wurman_dots_based_on_cell_count"
        )

    def __open_about_dialog(self) -> None:
        dialog = AboutDialog("wurman_dots")
        dialog.exec()
