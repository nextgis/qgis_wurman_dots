from typing import Any, Dict, Optional

from qgis.core import (
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant

from wurman_dots.processing.wurman_dots_algorithm import (
    GridType,
    WurmanDotsAlgorithm,
)


class AlgorithmForCellCount(WurmanDotsAlgorithm):
    GRID_COUNT = "GRID_COUNT"

    def tr(self, string: str, context: str = "") -> str:
        if context == "":
            context = self.__class__.__name__
        return QCoreApplication.translate(context, string)

    def createInstance(self) -> Optional[QgsProcessingAlgorithm]:
        return AlgorithmForCellCount()

    def name(self) -> str:
        return "create_wurman_dots_based_on_cell_count"

    def displayName(self) -> str:
        return self.tr("Create Wurman Dots (grid based on cell count)")

    def shortHelpString(self) -> str:
        return self.tr(
            "Create Wurman Dots using Square or Hexagonal grid. The grid is calculated based on the cell count."
        )

    def initAlgorithm(self, configuration: Dict[str, Any] = {}) -> None:  # noqa: B006
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input Point Layer"),
                [QgsProcessing.TypeVectorPoint],
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.GRID_COUNT,
                self.tr("Grid Cell Count"),
                defaultValue=10,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.GRID_TYPE,
                self.tr("Grid Type"),
                options=self.GRID_TYPES,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_FIXED_CIRCLES,
                self.tr("Fixed Circles"),
                QgsProcessing.TypeVectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_VAR_CIRCLES,
                self.tr("Variable Circles"),
                QgsProcessing.TypeVectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CONTINUOUS_FIXED_CIRCLES,
                self.tr("Create continuous grid of fixed circles"),
                defaultValue=False,
            )
        )

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: Optional[QgsProcessingFeedback],
    ) -> Dict[str, Any]:
        points_source = self.parameterAsSource(parameters, self.INPUT, context)
        if points_source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        cell_count = self.parameterAsDouble(
            parameters, self.GRID_COUNT, context
        )
        grid_type = self.parameterAsEnum(parameters, self.GRID_TYPE, context)
        continuous_grid = self.parameterAsBool(
            parameters, self.CONTINUOUS_FIXED_CIRCLES, context
        )

        fields = QgsFields()
        fields.append(QgsField("radius", QVariant.Double))
        fields.append(QgsField("numpoints", QVariant.Int))

        (sink_var, var_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_VAR_CIRCLES,
            context,
            fields,
            QgsWkbTypes.Polygon,
            points_source.sourceCrs(),
        )
        (sink_fixed, fixed_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_FIXED_CIRCLES,
            context,
            fields,
            QgsWkbTypes.Polygon,
            points_source.sourceCrs(),
        )

        extent = points_source.sourceExtent()
        extent_smaller_side = min(
            extent.xMaximum() - extent.xMinimum(),
            extent.yMaximum() - extent.yMinimum(),
        )
        grid_size = extent_smaller_side / cell_count

        grid_type = (
            GridType.SQUARE
            if self.GRID_TYPES[grid_type] == "Square"
            else GridType.HEXAGON
        )
        grid_layer = self.create_grid(grid_type, points_source, grid_size)

        self.create_circles(
            grid_layer, sink_var, sink_fixed, grid_size, continuous_grid
        )

        return {
            self.OUTPUT_VAR_CIRCLES: var_id,
            self.OUTPUT_FIXED_CIRCLES: fixed_id,
        }
