from wurman_points.wurman_points_plugin import WurmanPointsPlugin


def classFactory(iface):
    return WurmanPointsPlugin(iface)
