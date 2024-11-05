"""
Copyright start
MIT License
Copyright (c) 2024 Fortinet Inc
Copyright end
"""

from datetime import datetime

from requests import request, exceptions as req_exceptions
from connectors.core.connector import get_logger, ConnectorError

logger = get_logger('solarwinds-pingdom')


class SolarwindsPingdom:
    def __init__(self, config):
        self.base_url = config.get('server_url').strip('/')
        if not self.base_url.startswith('https://'):
            self.base_url = f'https://{self.base_url}'
        self.base_url = self.base_url + "/api/3.1"
        self.api_token = config['api_token']
        self.verify_ssl = config['verify_ssl']

    def make_rest_call(self, endpoint, method="GET", params=None, data=None):
        headers = {'Authorization': f"Bearer {self.api_token}"}
        service_endpoint = self.base_url + endpoint
        try:
            logger.debug(f"\n{method} {service_endpoint}\nparams: {params}\ndata: {data}")
            try:
                from connectors.debug_utils.curl_script import make_curl
                make_curl(method, service_endpoint, params=params, data=data, headers=headers, verify_ssl=self.verify_ssl)
            except Exception:
                pass
            response = request(method, service_endpoint, params=params, data=data, headers=headers, verify=self.verify_ssl)
            if response.ok:
                if response.text != "":
                    return response.json()
                else:
                    return True
            else:
                if response.text != "":
                    err_resp = response.text
                    error_msg = 'Response [{0}:Details: {1}]'.format(response.status_code, err_resp)
                else:
                    error_msg = 'Response [{0}:Details: {1}]'.format(response.status_code, response.content)
                logger.error(error_msg)
                raise ConnectorError(error_msg)
        except req_exceptions.SSLError:
            logger.error('An SSL error occurred')
            raise ConnectorError('An SSL error occurred')
        except req_exceptions.ConnectionError:
            logger.error('A connection error occurred')
            raise ConnectorError('A connection error occurred')
        except req_exceptions.Timeout:
            logger.error('The request timed out')
            raise ConnectorError('The request timed out')
        except req_exceptions.RequestException:
            logger.error('There was an error while handling the request')
            raise ConnectorError('There was an error while handling the request')
        except Exception as err:
            raise ConnectorError(str(err))


def build_params(params):
    new_params = {}
    for k, v in params.items():
        if v is False or v == 0 or v:
            new_params[k] = v
    return new_params


def convert_to_list(value):
    if not value:
        return value
    elif isinstance(value, list):
        return [x for x in value]
    elif isinstance(value, str):
        return [x for x in value.split(",")]
    elif isinstance(value, int):
        return [value]


def get_datetime(value):
    if isinstance(value, str):
        return int(datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
    return value


def get_alerts_list(config, params):
    ob = SolarwindsPingdom(config)
    params = build_params(params)
    checkids = params.get("checkids")
    _from = params.get("from")
    _to = params.get("to")
    status = params.get("status")
    userids = params.get("userids")
    fetch_all_records = params.pop("fetch_all_records", False)
    via = params.get("via")
    if checkids:
        params.update(checkids=convert_to_list(checkids))
    if _from:
        params.update({"from": get_datetime(_from)})
    if _to:
        params.update({"to": get_datetime(_to)})
    if status:
        params.update(status=convert_to_list(status))
    if userids:
        params.update(userids=convert_to_list(userids))
    if via:
        params.update(via=convert_to_list(via))
    alerts = True
    alerts_list = []
    offset = 0
    max_limit = 100
    if fetch_all_records and not isinstance(params.get("limit"), int):
        while alerts:
            params.update({"limit": max_limit, "offset": offset})
            response = ob.make_rest_call("/actions", params=params)
            alerts = response.get("actions", {}).get("alerts", [])
            logger.debug(f"fetched {len(alerts)} records for offset {offset}")
            alerts_list.extend(alerts)
            offset += max_limit
        actions = {"alerts": alerts_list}
        response["actions"] = actions
        logger.debug("fetched all records.")
        return response
    else:
        logger.debug("fetched data by limit.")
        return ob.make_rest_call("/actions", params=params)


def get_checks_list(config, params):
    ob = SolarwindsPingdom(config)
    params = build_params(params)
    tags = params.get("tags")
    if tags:
        params.update(tags=convert_to_list(tags))
    response = ob.make_rest_call("/checks", params=params)
    return response


def get_root_cause_analysis(config, params):
    ob = SolarwindsPingdom(config)
    params = build_params(params)
    _from = params.get("from")
    _to = params.get("to")
    if _from:
        params.update({"from": int(datetime.strptime(_from, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())})
    if _to:
        params.update({"to": int(datetime.strptime(_to, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())})
    response = ob.make_rest_call(f"/analysis/{params.pop('checkid')}", params=params)
    return response


def get_result_of_analysis(config, params):
    ob = SolarwindsPingdom(config)
    endpoint = f"/analysis/{params['checkid']}/{params['analysisid']}"
    response = ob.make_rest_call(endpoint)
    return response


def get_raw_test_results_list(config, params):
    ob = SolarwindsPingdom(config)
    params = build_params(params)
    probes = params.get("probes")
    status = params.get("status")
    _from = params.get("from")
    _to = params.get("to")
    if probes:
        params.update(probes=convert_to_list(probes))
    if status:
        params.update(status=convert_to_list(status))
    if _from:
        params.update({"from": int(datetime.strptime(_from, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())})
    if _to:
        params.update({"to": int(datetime.strptime(_to, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())})
    endpoint = f"/results/{params.pop('checkid')}"
    response = ob.make_rest_call(endpoint, params=params)
    return response


def _check_health(config):
    res = get_alerts_list(config, {"limit": 1})
    return True


operations = {
    "get_alerts_list": get_alerts_list,
    "get_checks_list": get_checks_list,
    "get_root_cause_analysis": get_root_cause_analysis,
    "get_result_of_analysis": get_result_of_analysis,
    "get_raw_test_results_list": get_raw_test_results_list
}
