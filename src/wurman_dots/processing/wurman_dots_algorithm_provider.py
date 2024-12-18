from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from wurman_dots.processing.algorithm_for_cell_count import (
    AlgorithmForCellCount,
)
from wurman_dots.processing.algorithm_for_cell_size import (
    AlgorithmForCellSize,
)


class WurmanDotsAlgorithmProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(AlgorithmForCellCount())
        self.addAlgorithm(AlgorithmForCellSize())

    def id(self) -> str:
        return "wurman_dots"

    def name(self) -> str:
        return self.tr("Wurman Dots")

    def icon(self) -> QIcon:
        return QIcon(":/plugins/wurman_dots/icons/wurman_dots.png")
