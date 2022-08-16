import re
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
        self,
        dashboards: list,
        app_id: int = None,
        metrics: str = None,
        metric_match: str = None,
    ):
        used_dashboards = []
        for i, dashboard in enumerate(dashboards, start=1):
            logging.debug(
                f"Dashboard [{i}/{len(dashboards)}][{dashboard['name']}] - Check Dashboard"
            )
            for widget in dashboard["widgets"]:
                if len(metrics) > 0:
                    self.__check_widget_by_app_and_metrics(
                        used_dashboards,
                        dashboard,
                        widget,
                        app_id,
                        metrics,
                        metric_match,
                    )
                else:
                    self.__check_widget_by_app(
                        used_dashboards, dashboard, widget, app_id
                    )

            logging.debug(
                f"Dashboard [{i}/{len(dashboards)}][{dashboard['name']}] - Dashboard checked"
            )
        return used_dashboards

    def __check_widget_by_app_and_metrics(
        self,
        used_dashboards: list,
        dashboard: dict,
        widget: dict,
        app_id: int,
        metrics: list,
        metric_match: str = None,
    ):
        for metric in metrics:
            if self.__check_if_widget_is_used(widget, app_id, metric, metric_match):
                self.__append_dashboard_and_widget(
                    used_dashboards, dashboard, widget, metric
                )

    def __check_widget_by_app(
        self, used_dashboards: list, dashboard: dict, widget: dict, app_id: int
    ):
        if self.__check_if_widget_is_used(widget, app_id):
            self.__append_dashboard_and_widget(used_dashboards, dashboard, widget)

    def __check_if_widget_is_used(
        self,
        widget: dict,
        app_id: int = None,
        metric: str = None,
        metric_match: str = None,
    ) -> boolean:
        if metric is not None:
            if widget["type"] in ["TIMESERIES_GRAPH", "PIE", "GAUGE", "METRIC_LABEL"]:
                return self.__check_metrics_widget_used_by_app(
                    widget, app_id, metric, metric_match
                )
            return False
        else:
            if widget["type"] in ["TIMESERIES_GRAPH", "PIE", "GAUGE", "METRIC_LABEL"]:
                return self.__check_metrics_widget_used_by_app(
                    widget, app_id, metric, metric_match
                )
            elif widget["type"] == "HEALTH_LIST":
                if app_id is None:
                    return False
                return self.__check_health_widget_used_by_app(widget, app_id)
            elif widget["type"] == "LIST":
                if app_id is None:
                    return False
                return self.__check_event_widget_used_by_app(widget, app_id)
            return False

    def __check_event_widget_used_by_app(self, widget: dict, app_id: int):
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
        self,
        widget: dict,
        app_id: int = None,
        metric: str = None,
        metric_match: str = None,
    ) -> boolean:
        if widget["widgetsMetricMatchCriterias"] is not None:

            if app_id is not None:
                app_ids = [
                    i["metricMatchCriteria"]["applicationId"]
                    for i in widget["widgetsMetricMatchCriterias"]
                    if self.__check_match(
                        i["metricMatchCriteria"]["metricExpression"]["inputMetricPath"],
                        metric,
                        metric_match,
                    )
                ]

                # Adapt compare here
                return app_id in app_ids
            else:
                matching_criterias = [
                    i
                    for i in widget["widgetsMetricMatchCriterias"]
                    if self.__check_match(
                        i["metricMatchCriteria"]["metricExpression"]["inputMetricPath"],
                        metric,
                        metric_match,
                    )
                ]
                return len(matching_criterias) > 0

        else:
            return False

    def __append_dashboard_and_widget(
        self, used_dashboards: list, dashboard: dict, widget: dict, metric: str = None
    ):
        used_dashboard = next(
            (i for i in used_dashboards if i["id"] == dashboard["id"]),
            None,
        )

        widget_dict = {"id": widget["id"], "title": widget["title"], "metrics": []}
        if metric is not None:
            widget_dict["metrics"].append(metric)

        if used_dashboard is None:
            used_dashboards.append(
                {
                    "id": dashboard["id"],
                    "name": dashboard["name"],
                    "widgets": [widget_dict],
                }
            )
        else:
            used_widget = next(
                (i for i in used_dashboard["widgets"] if i["id"] == widget["id"]),
                None,
            )
            if used_widget is None:
                used_dashboard["widgets"].append(widget_dict)
            elif metric is not None:
                used_widget["metrics"].append(metric)

    def __check_match(self, input: str, metric: str, metric_match: str):
        if metric is None:
            return True
        if input is None:
            return False

        if metric_match == "exact":
            return input == metric
        elif metric_match == "contains":
            return metric in input
        elif metric_match == "regex":
            metric_regex = re.compile(metric)
            return metric_regex.match(input)
        else:
            return False
