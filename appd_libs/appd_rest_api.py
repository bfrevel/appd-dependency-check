import requests
import logging


class AppdRestApi:
    def __init__(
        self,
        controller_url: str,
        client_id: str,
        client_secret: str,
        controller_certificate=None,
    ):
        self.controller_url = controller_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_token = None
        self.controller_certificate = controller_certificate

    def get(self, url, params=None, data=None, json=None, headers=None):
        return self.execute("GET", url, params, data, json, headers)

    def post(self, url, params=None, data=None, json=None, headers=None):
        return self.execute("POST", url, params, data, json, headers)

    def execute(self, method, url, params=None, data=None, json=None, headers=None):
        if self.client_token == None:
            self.client_token = self.get_bearer_token()

        request_url = f"{self.controller_url}{url}"
        request_headers = {} if headers == None else headers
        request_headers["Authorization"] = f"Bearer {self.client_token}"

        return self.__execute_request(
            method,
            request_url,
            params=params,
            data=data,
            json=json,
            headers=request_headers,
        )

    def __execute_request(
        self,
        method,
        url,
        params=None,
        data=None,
        json=None,
        headers=None,
        auth_retry=True,
    ):
        response = requests.request(
            method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            verify=self.controller_certificate,
        )

        if (
            auth_retry
            and response.status_code == 401
            and "invalid access token" in response.text
        ):
            logging.info("Retry - Generate new Token")
            self.client_token = self.get_bearer_token()
            headers["Authorization"] = f"Bearer {self.client_token}"
            response = requests.request(
                method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                verify=self.controller_certificate,
            )

        return response

    def get_bearer_token(self):
        url = f"{self.controller_url}/controller/api/oauth/access_token"
        headers = {"Content-Type": "application/vnd.appd.cntrl+protobuf;v=1"}
        data = f"grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}"

        try:
            response = requests.post(
                url, data=data, headers=headers, verify=self.controller_certificate
            )
            data = response.json()
            token = data["access_token"]
            logging.info(f"Generated Token: {token[:20]}...")
            return token
        except Exception as e:
            logging.error(f"Failed to authenticate: {type(e)}")
            raise e
