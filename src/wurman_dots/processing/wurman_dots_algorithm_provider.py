from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from wurman_points.processing.wurman_points_algorithm import (
    WurmanPointsAlgorithm,
)


class WurmanPointsAlgorithmProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(WurmanPointsAlgorithm())

    def id(self) -> str:
        return "wurman_points"

    def name(self) -> str:
        return self.tr("Wurman Points")

    def icon(self) -> QIcon:
        return QIcon(":/plugins/wurman_points/icons/wurman_points.png")
