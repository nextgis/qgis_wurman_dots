import processing
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingFeatureSource,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsRectangle,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant


class WurmanDotsAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    GRID_SIZE = "GRID_SIZE"
    GRID_TYPE = "GRID_TYPE"
    OUTPUT_VAR_CIRCLES = "OUTPUT_VAR_CIRCLES"
    OUTPUT_FIXED_CIRCLES = "OUTPUT_FIXED_CIRCLES"

    GRID_TYPES = ["Square", "Hexagonal"]

    def tr(self, string: str, context: str = "") -> str:
        if context == "":
            context = self.__class__.__name__
        return QCoreApplication.translate(context, string)

    def createInstance(self):
        return WurmanDotsAlgorithm()

    def name(self):
        return "create_wurman_dots"

    def displayName(self):
        return self.tr("Create Wurman Dots")

    def shortHelpString(self):
        return self.tr("Create Wurman Dots using Square or Hexagonal grid.")

    def initAlgorithm(self, configuration=None):
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

    def processAlgorithm(self, parameters, context, feedback):
        points_source = self.parameterAsSource(parameters, self.INPUT, context)
        if points_source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        grid_size = self.parameterAsDouble(parameters, self.GRID_SIZE, context)
        grid_type = self.parameterAsEnum(parameters, self.GRID_TYPE, context)

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

        if self.GRID_TYPES[grid_type] == "Square":
            grid_layer = self.create_square_grid(points_source, grid_size)
        else:
            grid_layer = self.create_hex_grid(points_source, grid_size)

        self.create_circles(grid_layer, sink_var, sink_fixed, grid_size)

        return {
            self.OUTPUT_VAR_CIRCLES: var_id,
            self.OUTPUT_FIXED_CIRCLES: fixed_id,
        }

    def create_square_grid(
        self, points_source: QgsProcessingFeatureSource, grid_size: float
    ):
        grid_layer = QgsVectorLayer(
            f"Polygon?crs={points_source.sourceCrs().authid()}",
            "grid",
            "memory",
        )
        provider = grid_layer.dataProvider()
        provider.addAttributes([QgsField("point_count", QVariant.Int)])
        grid_layer.updateFields()
        extent = points_source.sourceExtent()

        min_x = extent.xMinimum()
        min_y = extent.yMinimum()
        grid_features = {}

        for point in points_source.getFeatures():  # type: ignore
            x = point.geometry().asPoint().x()
            y = point.geometry().asPoint().y()
            cell_x = int((x - min_x) // grid_size) * grid_size + min_x
            cell_y = int((y - min_y) // grid_size) * grid_size + min_y
            cell_geom = QgsGeometry.fromRect(
                QgsRectangle(
                    cell_x, cell_y, cell_x + grid_size, cell_y + grid_size
                )
            )
            cell_id = f"{cell_x}_{cell_y}"

            if cell_id not in grid_features:
                grid_features[cell_id] = {
                    "geometry": cell_geom,
                    "point_count": 0,
                }
            grid_features[cell_id]["point_count"] += 1

        for feature_data in grid_features.values():
            feature = QgsFeature()
            feature.setGeometry(feature_data["geometry"])
            feature.setAttributes([feature_data["point_count"]])
            provider.addFeature(feature)

        return grid_layer

    def create_hex_grid(
        self, points_source: QgsProcessingFeatureSource, grid_size: float
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
            "TYPE": 4,
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

    def create_circles(self, grid_layer, sink_var, sink_fixed, grid_size):
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
            if point_count is None or point_count == 0:
                continue

            geom = feature.geometry()
            center = geom.centroid().asPoint()

            radius = (grid_size * 0.5) * (point_count / max_point_count)
            circle_geom = QgsGeometry.fromPointXY(center).buffer(radius, 32)

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
