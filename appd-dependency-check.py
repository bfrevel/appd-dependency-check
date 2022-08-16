#!/usr/bin/env python

import configparser
import time
import click
import sys


from appd_libs.appd_rest_api import AppdRestApi
from appd_libs.appd_applications import AppdApplications
from appd_libs.appd_dashboards import AppdDashboards


config = configparser.ConfigParser()
config.read("config.ini")

rest_api = AppdRestApi(
    config["controller"]["url"],
    config["controller"]["client_id"],
    config["controller"]["client_secret"],
)

appd_applications = AppdApplications(rest_api)
appd_dashboards = AppdDashboards(rest_api)


@click.command()
@click.option(
    "--application-id",
    help="search for this application ids in dashboards",
    type=int,
    multiple=True,
)
@click.option(
    "--application-name",
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
    type=click.Choice(["exact", "contains", "regex"]),
    default="exact",
    show_default=True,
)
def dashboards(application_id, application_name, metric, metric_match):
    """This command checks AppD Dashboards for existing metrics"""

    applications_to_check = get_applications_to_check(application_id, application_name)

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
def healthrules():
    """This command checks AppD HealthRules for existing metrics"""
    click.echo("comming soon...")


@click.group()
def group():
    pass


group.add_command(dashboards)
group.add_command(healthrules)


def get_applications_to_check(application_ids, application_names):

    if len(application_ids) > 0 or len(application_names) > 0:
        with click.progressbar(length=1, label="Load Application data") as bar:
            available_applications = appd_applications.get_applications()
            bar.update(1)

        applications_to_check = get_applications_to_check_by_id(
            application_ids, available_applications
        )
        applications_to_check += get_applications_to_check_by_name(
            application_names, available_applications
        )

        return list({i["id"]: i for i in applications_to_check}.values())
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
        dashboards_count_style = get_dashboard_count_style(dashboards_used)

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
                print_widget(widget)


def print_dashboards_metrics(dashboards, metrics):
    dashboards_count_style = get_dashboard_count_style(dashboards)
    metric_style = get_header_style(list(metrics))

    click.echo(f"Metrics {metric_style} are used in {dashboards_count_style} Dashboards")
    for dashboard in dashboards:
        print_dashboard(dashboard)

        for widget in dashboard["widgets"]:
            print_widget(widget)


def print_dashboard(dashboard):
    dashboard_name_style = click.style(dashboard["name"], bold=True)
    click.echo(f"\tDashboard: {dashboard_name_style} [{dashboard['id']}]")


def print_widget(widget):
    widget_name_style = (
        click.style(widget["title"], bold=True)
        if widget["title"] is not None
        else click.style("no title", bold=True, italic=True)
    )
    click.echo(f"\t\tWidget: {widget_name_style} [{widget['id']}]")
    print_metrics(widget["metrics"])


def print_metrics(metrics):
    for matched_metric in metrics:
        matched_metric_style = click.style(f"{matched_metric}", underline=True)
        click.echo(f"\t\t\tMetric: {matched_metric_style}")


def get_dashboard_count_style(dashboards):
    dashboards_count = len(dashboards)
    return click.style(
        str(dashboards_count),
        bold=True,
        fg="red" if dashboards_count > 0 else "green",
    )


def get_header_style(header):
    return click.style(header, bold=True)


if __name__ == "__main__":
    group()
