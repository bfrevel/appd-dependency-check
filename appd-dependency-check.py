#!/usr/bin/env python

import configparser
import click
import sys


from appd_libs.appd_rest_api import AppdRestApi
from appd_libs.appd_applications import AppdApplications
from appd_libs.appd_dashboards import AppdDashboards
from appd_libs.appd_healthrules import AppdHealthrules


config = configparser.ConfigParser()
config.read("config.ini")

rest_api = AppdRestApi(
    config.get("controller", "url"),
    config.get("controller", "client_id"),
    config.get("controller", "client_secret"),
)
appd_internal_applications = {
    "analytics_application_id": config.getint(
        "applications", "analytics_application_id", fallback=0
    ),
    "db_mon_application": config.getint(
        "applications", "db_mon_application", fallback=0
    ),
    "sim_application_id": config.getint(
        "applications", "sim_application_id", fallback=0
    ),
}


appd_applications = AppdApplications(rest_api)
appd_dashboards = AppdDashboards(rest_api)
appd_health_rules = AppdHealthrules(rest_api)


@click.command()
@click.option(
    "--app-id",
    help="search for this application ids in dashboards",
    type=int,
    multiple=True,
)
@click.option(
    "--app-name",
    help="search for this applications in dashboards",
    type=str,
    multiple=True,
)
@click.option(
    "--metric",
    help="search for this metric in dashboards",
    type=str,
    multiple=True,
)
@click.option(
    "--metric-match",
    help="defines how to match metrics",
    type=click.Choice(["contains", "contains_case_sensitive", "exact", "regex"]),
    default="contains",
    show_default=True,
)
def dashboards(app_id, app_name, metric, metric_match):
    """This command checks AppD Dashboards for existing metrics"""

    applications_to_check = get_applications_to_check(app_id, app_name)

    with click.progressbar(length=1, label="Load Dashboards") as bar:
        dashboards = appd_dashboards.get_dashboards()
        bar.update(1)

    dashboards_details = []
    with click.progressbar(dashboards, label="Load Dashboard details") as bar:
        for dashboard in bar:
            dashboards_details.append(appd_dashboards.get_dashboard(dashboard["id"]))

    if len(applications_to_check) > 0:
        with click.progressbar(
            applications_to_check,
            label=f"Check Dashboards for Applications{' and Metrics' if len(metric) > 0 else ''}",
        ) as bar:
            for app in bar:
                app[
                    "dashboards_used"
                ] = appd_dashboards.get_dashboards_used_by_app_and_metric(
                    dashboards_details,
                    app["id"],
                    metrics=metric,
                    metric_match=metric_match,
                )

        print_dashboards_applications(applications_to_check, metric)

    elif len(metric) > 0:
        with click.progressbar(length=1, label=f"Check Dashboards for Metrics") as bar:
            dashboards_used = appd_dashboards.get_dashboards_used_by_app_and_metric(
                dashboards_details, metrics=metric, metric_match=metric_match
            )
            bar.update(1)

        print_dashboards_metrics(dashboards_used, metric)

    else:
        click.echo(f"Neither application, nor metrics is set", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--app-id",
    help="search for this application ids in dashboards",
    type=int,
    multiple=True,
)
@click.option(
    "--app-name",
    help="search for this applications in dashboards",
    type=str,
    multiple=True,
)
@click.option(
    "--metric",
    help="search for this metric in healthrules",
    type=str,
    multiple=True,
    required=True,
)
@click.option(
    "--metric-match",
    help="defines how to match metrics",
    type=click.Choice(["contains", "contains_case_sensitive", "exact", "regex"]),
    default="contains",
    show_default=True,
)
def healthrules(app_id, app_name, metric, metric_match):
    """This command checks AppD Dashboards for existing metrics"""

    applications_to_check = get_applications_to_check(app_id, app_name, True)

    with click.progressbar(
        applications_to_check,
        label=f"Load HealthRules for Application",
    ) as bar:
        for app in bar:
            app["healthrules"] = appd_health_rules.get_healthrules(app["id"])

    for app in applications_to_check:
        with click.progressbar(
            app["healthrules"],
            label=f"Load HealthRules Details for Application {app['name']}",
        ) as bar2:
            for healthrule in bar2:
                healthrule["details"] = appd_health_rules.get_healthrule(
                    app["id"], healthrule["id"]
                )
                if (
                    "id" in healthrule["details"]
                    and "name" in healthrule["details"]
                    and "evalCriterias" in healthrule["details"]
                ):
                    healthrule["json_valid"] = True
                else:
                    click.echo(
                        f'{get_error()}JSON for healthrule {healthrule["name"]}:[{healthrule["id"]}] in application {app["name"]}[id:{app["id"]}] is not valid',
                        err=True,
                    )
                    healthrule["json_valid"] = False

    for app in applications_to_check:
        app["match"] = False
        for healthrule in app["healthrules"]:
            if healthrule["json_valid"]:
                healthrule["match"] = appd_health_rules.check_healthrule_by_metrics(
                    app, healthrule["details"], metric, metric_match
                )
                if (
                    healthrule["match"]["criticalCriteria"]
                    or healthrule["match"]["warningCriteria"]
                    or healthrule["match"]["informationPoint"]
                ):
                    app["match"] = True
            else:
                healthrule["match"] = None
    applications_mached = [app for app in applications_to_check if app["match"]]

    click.echo(
        f"Metrics {get_header_style(list(metric))} are used in {get_count_style(applications_mached)} Healthrules"
    )

    for app in applications_to_check:
        if app["match"]:
            click.echo(f"\tApplication: {get_header_style(app['name'])} [{app['id']}]")
            for healthrule in app["healthrules"]:
                if healthrule["match"]:
                    if healthrule["match"]["criticalCriteria"]:
                        click.echo(
                            f"\t\tHealthrule: {get_header_style(healthrule['name'])} [{healthrule['id']}], CriticalCriteria"
                        )
                    if healthrule["match"]["warningCriteria"]:
                        click.echo(
                            f"\t\tHealthrule: {get_header_style(healthrule['name'])} [{healthrule['id']}], WriticalCriteria"
                        )
                    if healthrule["match"]["informationPoint"]:
                        click.echo(
                            f"\t\tHealthrule: {get_header_style(healthrule['name'])} [{healthrule['id']}], InformationPoint"
                        )


@click.group()
def group():
    pass


group.add_command(dashboards)
group.add_command(healthrules)


def get_applications_to_check(
    application_ids, application_names, fallback_all: bool = False
):
    all_apps = appd_applications.get_applications()

    if appd_internal_applications["analytics_application_id"] != 0:
        all_apps.append(
            appd_applications.get_application(
                appd_internal_applications["analytics_application_id"]
            )
        )

    if appd_internal_applications["db_mon_application"] != 0:
        all_apps.append(
            appd_applications.get_application(
                appd_internal_applications["db_mon_application"]
            )
        )

    if appd_internal_applications["sim_application_id"] != 0:
        all_apps.append(
            appd_applications.get_application(
                appd_internal_applications["sim_application_id"]
            )
        )

    with click.progressbar(length=1, label="Load Application data") as bar:
        all_apps
        bar.update(1)

    if len(application_ids) > 0 or len(application_names) > 0:
        applications_to_check = get_applications_to_check_by_id(
            application_ids, all_apps
        )
        applications_to_check += get_applications_to_check_by_name(
            application_names, all_apps
        )

        return list({i["id"]: i for i in applications_to_check}.values())

    elif fallback_all:
        return [{"id": i["id"], "name": i["name"]} for i in all_apps]
    else:
        return []


def get_applications_to_check_by_id(application_ids, available_applications):
    applications_to_check = []

    if len(application_ids) > 0:
        click.echo(f"Checking Application Ids {list(application_ids)}")

        with click.progressbar(application_ids, label="Load Application Ids") as bar:
            for app_id in bar:
                app_name = next(
                    (
                        item["name"]
                        for item in available_applications
                        if item["id"] == app_id
                    ),
                    None,
                )
                if app_name is None:
                    app_id_style = click.style(app_id, bold=True, fg="red")
                    click.echo(
                        f"Application Id {app_id_style} is not available", err=True
                    )
                    sys.exit(1)
                applications_to_check.append(
                    {
                        "id": app_id,
                        "name": app_name,
                    }
                )
    return applications_to_check


def get_applications_to_check_by_name(application_names, available_applications):
    applications_to_check = []

    if len(application_names) > 0:
        click.echo(f"Checking Application Names {list(application_names)}")

        with click.progressbar(
            application_names, label="Load Application Names"
        ) as bar:
            for app_name in bar:
                app_id = next(
                    (i["id"] for i in available_applications if i["name"] == app_name),
                    None,
                )
                if app_id is None:
                    app_name_style = click.style(app_name, bold=True, fg="red")
                    click.echo(
                        f"Application Name {app_name_style} is not available",
                        err=True,
                    )
                    sys.exit(1)
                applications_to_check.append(
                    {
                        "id": app_id,
                        "name": app_name,
                    }
                )

    return applications_to_check


def print_dashboards_applications(applications, metrics):
    for application in applications:
        application_name_style = get_header_style(application["name"])
        dashboards_used = application["dashboards_used"]
        dashboards_count_style = get_count_style(dashboards_used)

        if len(metrics) == 0:
            click.echo(
                f"Application {application_name_style} [{application['id']}] is used in {dashboards_count_style} Dashboards"
            )
        else:
            metric_style = get_header_style(list(metrics))
            click.echo(
                f"Application {application_name_style} [{application['id']}] and Metrics {metric_style} are used in {dashboards_count_style} Dashboards"
            )
        for dashboard in dashboards_used:
            print_dashboard(dashboard)

            for widget in dashboard["widgets"]:
                print_dashboard_widget(widget)


def print_dashboards_metrics(dashboards, metrics):
    dashboards_count_style = get_count_style(dashboards)
    metric_style = get_header_style(list(metrics))

    click.echo(
        f"Metrics {metric_style} are used in {dashboards_count_style} Dashboards"
    )
    for dashboard in dashboards:
        print_dashboard(dashboard)

        for widget in dashboard["widgets"]:
            print_dashboard_widget(widget)


def print_dashboard(dashboard):
    dashboard_name_style = click.style(dashboard["name"], bold=True)
    click.echo(f"\tDashboard: {dashboard_name_style} [{dashboard['id']}]")


def print_dashboard_widget(widget):
    widget_name_style = (
        click.style(widget["title"], bold=True)
        if widget["title"] is not None
        else click.style("no title", bold=True, italic=True)
    )
    click.echo(f"\t\tWidget: {widget_name_style} [{widget['id']}]")
    print_dashboard_metrics(widget["metrics"])


def print_dashboard_metrics(metrics):
    for matched_metric in metrics:
        matched_metric_style = click.style(f"{matched_metric}", underline=True)
        click.echo(f"\t\t\tMetric: {matched_metric_style}")


def get_count_style(elements):
    elements_count = len(elements)
    return click.style(
        str(elements_count),
        bold=True,
        fg="red" if elements_count > 0 else "green",
    )


def get_info():
    return f'[{click.style(str("INFO"),bold=True,fg="green")}]'


def get_warn():
    return f'[{click.style(str("WARN"),bold=True,fg="yellow")}]'


def get_error():
    return f'[ {click.style(str("ERR"),bold=True,fg="red")}]'


def get_header_style(header):
    return click.style(header, bold=True)


if __name__ == "__main__":
    group()
