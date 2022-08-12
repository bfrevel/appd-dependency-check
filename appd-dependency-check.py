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
# @click.option("--application-names", help='search for this application id in dashboards', type=int)
# @click.option("--aws-stack-name", prompt=False, help='Unique AWS CloudFormation stack name for the region', type=str, default=AWS_STACK_NAME, show_default=True, callback=validate_length)


def dashboards(application_id, application_name, metric):
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
                    dashboards_details, app["id"], metric
                )

        for application in applications_to_check:
            output_name_style = click.style(application["name"], bold=True)
            dashboards_count = len(application["dashboards_used"])
            dashboards_count_style = click.style(
                str(dashboards_count),
                bold=True,
                fg="red" if dashboards_count > 0 else "green",
            )

            click.echo(
                f"Application {output_name_style} [{application['id']}]{' (and Metrics) are' if len(metric) > 0 else ' is'} used in {dashboards_count_style} Dashboards"
            )
            for dashboard in application["dashboards_used"]:
                click.echo(f"\t[{dashboard['id']}] {dashboard['name']}")

    elif len(metric) > 0:
        with click.progressbar(length=1, label=f"Check Dashboards for Metrics") as bar:
            dashboards_used = appd_dashboards.get_dashboards_used_by_app_and_metric(
                dashboards_details, metrics=metric
            )
            bar.update(1)

        output_name_style = click.style(metric, bold=True)
        dashboards_count = len(dashboards_used)
        dashboards_count_style = click.style(
            str(dashboards_count),
            bold=True,
            fg="red" if dashboards_count > 0 else "green",
        )

        click.echo(
            f"Metrics {output_name_style} is used in {dashboards_count_style} Dashboards"
        )
        for dashboard in dashboards_used:
            click.echo(f"\t[{dashboard['id']}] {dashboard['name']}")
    else:
        click.echo(f"Neither application, nor metrics is set", err=True)
        sys.exit(1)


@click.command()
def healthrules():
    """This command checks AppD HealthRules for existing metrics"""
    click.echo("comming soon...")


@click.command()
def applications():
    """This command lists all available AppD applications"""

    appd_applications = AppdApplications(rest_api)

    with click.progressbar(length=1, label="Load Applications") as bar:
        apps = appd_applications.get_applications()
        bar.update(1)

    with click.progressbar(apps, label="Load Application Details") as bar:
        for app in bar:
            appd_applications.get_application(app["id"])


@click.group()
def group():
    pass


group.add_command(dashboards)
group.add_command(healthrules)
group.add_command(applications)


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

        return list({v["id"]: v for v in applications_to_check}.values())
    else:
        return []


def get_applications_to_check_by_id(application_ids, available_applications):
    applications_to_check = []

    if len(application_ids) > 0:
        click.echo(f"Checking Application Ids {application_ids}")

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

        click.echo(f"Checking Application Names {application_names}")

        with click.progressbar(
            application_names, label="Load Application Names"
        ) as bar:
            for app_name in bar:
                app_id = next(
                    (
                        item["id"]
                        for item in available_applications
                        if item["name"] == app_name
                    ),
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


if __name__ == "__main__":
    group()
