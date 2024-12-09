from enum import IntEnum
from typing import Any, Dict, Optional

import processing
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeatureSource,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant


class GridType(IntEnum):
    SQUARE = 2
    HEXAGON = 4


class WurmanDotsAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    GRID_SIZE = "GRID_SIZE"
    GRID_TYPE = "GRID_TYPE"
    OUTPUT_VAR_CIRCLES = "OUTPUT_VAR_CIRCLES"
    OUTPUT_FIXED_CIRCLES = "OUTPUT_FIXED_CIRCLES"
    CONTINUOUS_FIXED_CIRCLES = "CONTINUOUS_FIXED_CIRCLES"

    GRID_TYPES = ["Square", "Hexagonal"]

    def tr(self, string: str, context: str = "") -> str:
        if context == "":
            context = self.__class__.__name__
        return QCoreApplication.translate(context, string)

    def createInstance(self) -> Optional[QgsProcessingAlgorithm]:
        return WurmanDotsAlgorithm()

    def name(self) -> str:
        return "create_wurman_dots"

    def displayName(self) -> str:
        return self.tr("Create Wurman Dots")

    def shortHelpString(self) -> str:
        return self.tr("Create Wurman Dots using Square or Hexagonal grid.")

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
                self.GRID_SIZE,
                self.tr("Grid Cell Size (meters)"),
                defaultValue=50000,
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

        grid_size = self.parameterAsDouble(parameters, self.GRID_SIZE, context)
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

    def create_grid(
        self,
        grid_type: GridType,
        points_source: QgsProcessingFeatureSource,
        grid_size: float,
    ):
        extent = points_source.sourceExtent()
        buffer_size = grid_size * 0.5
        expanded_extent = QgsRectangle(
            extent.xMinimum() - buffer_size,
            extent.yMinimum() - buffer_size,
            extent.xMaximum() + buffer_size,
            extent.yMaximum() + buffer_size,
        )

        params = {
            "TYPE": int(grid_type),
            "EXTENT": f"{expanded_extent.xMinimum()},{expanded_extent.xMaximum()},{expanded_extent.yMinimum()},{expanded_extent.yMaximum()} [{points_source.sourceCrs().authid()}]",
            "HSPACING": grid_size,
            "VSPACING": grid_size,
            "CRS": points_source.sourceCrs(),
            "OUTPUT": "memory:",
        }
        hex_grid = processing.run("native:creategrid", params)["OUTPUT"]
        provider = hex_grid.dataProvider()
        provider.addAttributes([QgsField("point_count", QVariant.Int)])
        hex_grid.updateFields()

        # spatial_index = QgsSpatialIndex(points_source.getFeatures())
        for hexagon in hex_grid.getFeatures():
            hex_geom = hexagon.geometry()
            if not hex_geom or hex_geom.isEmpty():
                continue

            point_count = sum(
                1
                for point in points_source.getFeatures()  # type: ignore
                if hex_geom.intersects(point.geometry())
            )
            hexagon.setAttribute("point_count", point_count)
            provider.addFeature(hexagon)

        return hex_grid

    def create_circles(
        self,
        grid_layer,
        sink_var,
        sink_fixed,
        grid_size,
        continuous_grid: bool,
    ):
        features = list(grid_layer.getFeatures())
        if not features:
            return

        max_point_count = max(
            [
                f["point_count"]
                for f in features
                if f["point_count"] is not None
            ],
            default=1,
        )

        for feature in features:
            point_count = feature["point_count"]
            if (
                point_count is None or point_count == 0
            ) and not continuous_grid:
                continue

            geom = feature.geometry()
            center = geom.centroid().asPoint()
            if point_count is not None and point_count != 0:
                radius = (grid_size * 0.5) * (point_count / max_point_count)
                circle_geom = QgsGeometry.fromPointXY(center).buffer(
                    radius, 32
                )

                var_circle = QgsFeature()
                var_circle.setGeometry(circle_geom)
                var_circle.setAttributes([radius, point_count])
                sink_var.addFeature(var_circle)

            fixed_radius = grid_size * 0.5
            fixed_geom = QgsGeometry.fromPointXY(center).buffer(
                fixed_radius, 32
            )

            fixed_circle = QgsFeature()
            fixed_circle.setGeometry(fixed_geom)
            fixed_circle.setAttributes([fixed_radius, point_count])
            sink_fixed.addFeature(fixed_circle)
