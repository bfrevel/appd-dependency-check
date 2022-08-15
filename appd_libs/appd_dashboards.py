from xmlrpc.client import boolean, boolean
from .appd_rest_api import AppdRestApi
import logging


class AppdDashboards:
    def __init__(self, appd_api: AppdRestApi):
        self.appd_api: AppdRestApi = appd_api

    def get_dashboards(self):
        url = f"/controller/restui/dashboards/getAllDashboardsByType/false"
        try:
            response = self.appd_api.get(url)
            data = response.json()
            logging.info(f"Number of Dashboards: {len(data)}")

            dashboards = []
            for i, dashboard in enumerate(data, start=1):
                logging.debug(
                    f"Dashboard [{i}/{len(data)}][{dashboard['name']}] - Load Dashboard details"
                )
                dashboards.append(self.get_dashboard(dashboard["id"]))
                logging.debug(
                    f"Dashboard [{i}/{len(data)}][{dashboard['name']}] - Loaded Dashboard details"
                )

            return dashboards
        except Exception as e:
            logging.error(f"Failed to load dashboards: {type(e)}")
            raise e

    def get_dashboard(self, id: int):
        url = f"/controller/restui/dashboards/dashboardIfUpdated/{id}/-1"
        try:
            response = self.appd_api.get(url)
            data = response.json()
            return data
        except Exception as e:
            logging.error(f"Failed to load dashboard: {type(e)}")
            raise e

    def get_dashboards_used_by_app_and_metric(
        self, dashboards: list, app_id: int = None, metrics: str = None
    ):
        try:
            used_dashboards = []
            for i, dashboard in enumerate(dashboards, start=1):
                logging.debug(
                    f"Dashboard [{i}/{len(dashboards)}][{dashboard['name']}] - Check Dashboard"
                )
                for widget in dashboard["widgets"]:
                    if len(metrics) > 0:
                        for metric in metrics:
                            if self.__check_if_widget_is_used(widget, app_id, metric):
                                self.__append_dashboard_and_widget(
                                    used_dashboards, dashboard, widget, metric
                                )
                    else:
                        if self.__check_if_widget_is_used(widget, app_id):
                            self.__append_dashboard_and_widget(
                                used_dashboards, dashboard, widget
                            )

                logging.debug(
                    f"Dashboard [{i}/{len(dashboards)}][{dashboard['name']}] - Dashboard checked"
                )
            return used_dashboards
        except Exception as e:
            logging.error(f"Failed to map dashboards: {type(e)}")
            raise e

    def __check_if_widget_is_used(
        self, widget: dict, app_id: int = None, metric: str = None
    ) -> boolean:
        if metric is not None: 
            if widget["type"] in ["TIMESERIES_GRAPH", "PIE", "GAUGE", "METRIC_LABEL"]:
                return self.__check_metrics_widget_used_by_app(widget, app_id, metric)
            return False
        else: 
            if widget["type"] in ["TIMESERIES_GRAPH", "PIE", "GAUGE", "METRIC_LABEL"]:
                return self.__check_metrics_widget_used_by_app(widget, app_id, metric)
            elif widget["type"] == "HEALTH_LIST":
                if app_id is None:
                    return False
                return self.__check_health_widget_used_by_app(widget, app_id)
            elif widget["type"] == "LIST":
                if app_id is None:
                    return False
                return self.__check_event_widget_used_by_app(widget, app_id)
            return False

    def __check_event_widget_used_by_app(self, widget, app_id):
        if (
            widget["eventFilter"] is not None
            and widget["eventFilter"]["applicationIds"] is not None
        ):
            for entity_id in widget["eventFilter"]["applicationIds"]:
                if entity_id == app_id:
                    return True
        return False

    def __check_health_widget_used_by_app(self, widget: dict, app_id: int) -> boolean:
        if widget["applicationId"] != 0:
            return widget["applicationId"] == app_id
        elif widget["entityType"] == "APPLICATION":
            for entity_id in widget["entityIds"]:
                if entity_id == app_id:
                    return True
        return False

    def __check_metrics_widget_used_by_app(
        self, widget: dict, app_id: int = None, metric: str = None
    ) -> boolean:
        if widget["widgetsMetricMatchCriterias"] is not None:

            if app_id is not None:
                app_ids = [
                    criteria["metricMatchCriteria"]["applicationId"]
                    for criteria in widget["widgetsMetricMatchCriterias"]
                    if metric is None
                    or criteria["metricMatchCriteria"]["metricExpression"][
                        "inputMetricPath"
                    ]
                    == metric
                ]

                return app_id in app_ids
            else:
                matching_criterias = [
                    criteria
                    for criteria in widget["widgetsMetricMatchCriterias"]
                    if criteria["metricMatchCriteria"]["metricExpression"][
                        "inputMetricPath"
                    ]
                    == metric
                ]
                return len(matching_criterias) > 0

        else:
            return False

    def __append_dashboard_and_widget(
        self, used_dashboards, dashboard, widget, metric: str = None
    ):
        used_dashboard = next(
            (item for item in used_dashboards if item["id"] == dashboard["id"]),
            None,
        )

        widget_dict = {"id": widget["id"]}
        if metric is not None:
            widget_dict["metric"] = metric

        if used_dashboard is not None:
            used_dashboard["widgets"].append(widget_dict)
        else:
            used_dashboards.append(
                {
                    "id": dashboard["id"],
                    "name": dashboard["name"],
                    "widgets": [widget_dict],
                }
            )
