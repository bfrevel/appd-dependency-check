import re

import click
from .appd_rest_api import AppdRestApi
import logging


class AppdHealthrules:
    def __init__(self, appd_api: AppdRestApi):
        self.appd_api: AppdRestApi = appd_api

    def get_healthrules(self, app_id: int):
        url = f"/controller/alerting/rest/v1/applications/{app_id}/health-rules"
        try:
            response = self.appd_api.get(url)
            data = response.json()
            logging.info(f"Number of HealthRules: {len(data)}")
            return data
        except Exception as e:
            logging.error(f"Failed to load HealthRules: {type(e)}")
            raise e

    def get_healthrule(self, app_id: int, health_rule_id: int):
        url = f"/controller/alerting/rest/v1/applications/{app_id}/health-rules/{health_rule_id}"
        try:
            response = self.appd_api.get(url)
            data = response.json()
            return data
        except Exception as e:
            logging.error(f"Failed to load HealthRule: {type(e)}")
            raise e

    def check_healthrule_by_metrics(
        self,
        app: dict,
        healthrule: dict,
        metrics: list,
        metric_match: str,
    ):
        match_result = {
            "criticalCriteria": False,
            "warningCriteria": False,
            "informationPoint": False,
        }

        try:
            if (
                healthrule["affects"]["affectedEntityType"] == "INFORMATION_POINTS"
                and healthrule["affects"]["affectedInformationPoints"][
                    "informationPointScope"
                ]
                == "SPECIFIC_INFORMATION_POINTS"
            ):
                affected_information_points = healthrule["affects"][
                    "affectedInformationPoints"
                ]["informationPoints"]
                match_result["informationPoint"] = self.__check_affected_entities(
                    affected_information_points,
                    metrics,
                    metric_match,
                )

            if healthrule["evalCriterias"]["criticalCriteria"] is not None:
                match_result["criticalCriteria"] = self.__check_criteria(
                    healthrule["evalCriterias"]["criticalCriteria"],
                    metrics,
                    metric_match,
                )

            if healthrule["evalCriterias"]["warningCriteria"] is not None:
                match_result["warningCriteria"] = self.__check_criteria(
                    healthrule["evalCriterias"]["warningCriteria"],
                    metrics,
                    metric_match,
                )
        except Exception as e:
            click.echo(f'Healthrule in application {app["name"]}: Invalid JSON', e)

        return match_result

    def __check_affected_entities(
        self, entities: dict, metrics: list, metric_match: str
    ):
        for entity in entities:
            for metric in metrics:
                if self.__check_match(entity, metric, metric_match):
                    return True

    def __check_criteria(self, criteria: dict, metrics: list, metric_match: str):
        for condition in criteria["conditions"]:
            for metric in metrics:
                if condition["evalDetail"]["evalDetailType"] == "METRIC_EXPRESSION":
                    for expression_variable in condition["evalDetail"][
                        "metricExpressionVariables"
                    ]:
                        if self.__check_match(
                            expression_variable["metricPath"], metric, metric_match
                        ):
                            return True
                elif condition["evalDetail"]["evalDetailType"] == "SINGLE_METRIC":
                    if self.__check_match(
                        condition["evalDetail"]["metricPath"], metric, metric_match
                    ):
                        return True

    def __check_match(self, input: str, metric: str, metric_match: str):
        if metric is None:
            return True
        if input is None:
            return False

        if metric_match == "exact":
            return input == metric
        elif metric_match == "contains":
            return re.search(metric, input, re.IGNORECASE)
        elif metric_match == "contains_case_sensitive":
            return re.search(metric, input)
        elif metric_match == "regex":
            metric_regex = re.compile(metric)
            return metric_regex.match(input)
        else:
            return False
