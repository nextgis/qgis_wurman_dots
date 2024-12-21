from enum import IntEnum

import processing
from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsGeometry,
    QgsProcessingAlgorithm,
    QgsProcessingFeatureSource,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant


class GridType(IntEnum):
    SQUARE = 2
    HEXAGON = 4


class WurmanDotsAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    GRID_TYPE = "GRID_TYPE"
    OUTPUT_VAR_CIRCLES = "OUTPUT_VAR_CIRCLES"
    OUTPUT_FIXED_CIRCLES = "OUTPUT_FIXED_CIRCLES"
    CONTINUOUS_FIXED_CIRCLES = "CONTINUOUS_FIXED_CIRCLES"

    GRID_TYPES = ["Square", "Hexagonal"]

    def create_grid(
        self,
        grid_type: GridType,
        points_source: QgsProcessingFeatureSource,
        grid_size: float,
        expanded_extent: QgsRectangle,
    ) -> QgsVectorLayer:
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
        grid_layer: QgsVectorLayer,
        sink_var: QgsFeatureSink,
        sink_fixed: QgsFeatureSink,
        grid_size: float,
        continuous_grid: bool,
    ) -> None:
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
