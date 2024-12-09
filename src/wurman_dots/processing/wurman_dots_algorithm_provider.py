from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from wurman_dots.processing.wurman_dots_algorithm import (
    WurmanDotsAlgorithm,
)


class WurmanDotsAlgorithmProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(WurmanDotsAlgorithm())

    def id(self) -> str:
        return "wurman_dots"

    def name(self) -> str:
        return self.tr("Wurman Dots")

    def icon(self) -> QIcon:
        return QIcon(":/plugins/wurman_dots/icons/wurman_dots.png")
