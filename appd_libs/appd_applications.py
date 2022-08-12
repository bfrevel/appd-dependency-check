from .appd_rest_api import AppdRestApi
import logging


class AppdApplications:
    def __init__(self, appd_rest_api: AppdRestApi):
        self.appd_rest_api: AppdRestApi = appd_rest_api

    def get_applications(self):
        url = f"/controller/rest/applications?output=JSON"
        try:
            response = self.appd_rest_api.get(url)
            data = response.json()
            logging.info(f"Number of Apps: {len(data)}")
            return data
        except Exception as e:
            logging.error(f"Failed to load applications: {type(e)}")
            raise e

    def get_application(self, id: int):
        url = f"/controller/rest/applications/{id}?output=JSON"
        try:
            response = self.appd_rest_api.get(url)
            data = response.json()
            logging.debug(f"Loaded application:[{id}]")
            if len(data) != 1:
                raise ValueError("Invalid Application Id")
            return data[0]
        except Exception as e:
            logging.error(f"Failed to load application: {type(e)}")
            raise ValueError("Invalid Application Id")
