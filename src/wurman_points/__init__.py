from wurman_points.plugin import WurmanPointsPluginInterface


def classFactory(iface):
    return WurmanPointsPluginInterface(iface)
