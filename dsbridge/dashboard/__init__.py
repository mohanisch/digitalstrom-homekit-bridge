"""
Dashboard
"""

from io import BytesIO
import os
import time
import psutil
import base36

import prometheus_client
from flask import Flask, render_template, redirect, request, Response
from pyqrcode import QRCode
from waitress import serve

from dsbridge import config
from dsbridge.helper import read_config, write_config
from dsbridge.metrics import REQUESTS, SYSTEM_USAGE

from dsbridge.digitalstrom import state_collector, device_collector
from dsbridge.digitalstrom.helper import create_application_token

from dsbridge.homekit import homekit
from dsbridge.homekit import start_homekit, stop_homekit

http = Flask(__name__)
http.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
http.config['TEMPLATES_AUTO_RELOAD'] = True
http.jinja_env.auto_reload = True


@http.route("/")
def root():
    """
    Main entrypoint
    """
    REQUESTS.inc()

    if 'token' not in config.read_config_file():
        return redirect("/onboarding/start", code=302)

    # from ..digitalstrom import state_collector
    entities = config.read_config_file()['entities']
    states = state_collector.gather_devices_status()

    res = {}
    for item in entities:
        if item['entity_id'] in states:
            item.update({"state": states[item['entity_id']]})
        res.setdefault(item['zone'], []).append(item)

    return render_template(
        'dashboard_main.html',
        entities=res
    )


@http.route("/metrics")
def metrics():
    """
    Responding metrics
    """
    content_type_latest = str('text/plain; version=0.0.4; charset=utf-8')

    SYSTEM_USAGE.labels('cpu_percent').set(psutil.Process(os.getpid()).cpu_percent())
    SYSTEM_USAGE.labels('memory_usage').set(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024)
    return Response(prometheus_client.generate_latest(), mimetype=content_type_latest)


@http.route("/homekit/state")
def homekit_state():
    """
    Returning true if homekit is paired
    """
    state = homekit.bridge_state()
    return str(state.paired)


@http.route("/save-devices", methods=['POST'])
def save_devices():
    """
    Saving devices
    """
    request_data = request.get_json()

    devices = request_data['devices']
    devices_subapplication = request_data['device_subapplication']

    entities = device_collector.get_entities()

    device_obj = []
    for device in devices:
        dev = ({v['entity_id']: v for v in entities}).get(device)
        if devices_subapplication.get(device):
            dev['service'] = devices_subapplication.get(device)
        device_obj.append(dev)

    zoneids = []
    for i in device_obj:
        if 'zoneid' in i:
            zoneids.append(i['zoneid'])

    #zoneids = {[i['zoneid'] for i in device_obj if 'zoneid' in i]}

    zone_obj = []
    for zoneid in zoneids:
        zone_devices = device_collector.get_zone(zoneid)['devices']
        zone = {
            "id": zoneid,
            "applications": zone_devices
        }
        zone_obj.append(zone)

    write_config(config.args.config_path + '/config.yml', {'entities': device_obj, 'zones': zone_obj})
    restart_bridge()
    return {"ok": True}


@http.route("/api/requesttoken", methods=['GET', 'POST'])
def request_token():
    """
    Getting password from user input and requests a token on ds server
    """
    response = None
    if request.method == 'POST':
        # modify/update the information for <user_id>
        password = request.form.get('password')
        response = create_application_token(password)

    if response['ok']:
        data = {"token": response['token']}
        write_config(config.args.config_path + '/config.yml', data)

    return response


@http.route("/restart-bridge", methods=['POST'])
def restart_bridge():
    """
    Restart bridge after user request
    """
    stop_homekit()
    time.sleep(2.4)
    start_homekit()

    return {"success": True}


@http.route("/onboarding/<step>", methods=['GET'])
def onboarding(step):
    """
    Handling the onboarding steps
    """
    dstoken = False
    initial_config = False
    paired = False

    if dstoken:
        step = 'devices'
    if initial_config:
        step = 'pairing'
    if paired:
        return redirect("/", code=302)

    if step == 'start':
        return render_template(
            'onboarding_main.html'
        )
    if step == 'devices':

        entities = device_collector.get_entities()
        cur_config = read_config(config.args.config_path + '/config.yml')

        res = {}
        for item in entities:
            if "entities" in cur_config:
                item.update({
                    'configured': any(item['entity_id'] in d['entity_id'] for d in cur_config['entities'])
                })
            res.setdefault(item['zone'], []).append(item)

        return render_template(
            'onboarding_devices.html',
            entities=res
        )
    if step == 'pairing':
        bridge_state = homekit.bridge_state()
        stream = BytesIO()
        QRCode(xhm_uri(bridge_state.pincode, bridge_state.setup_id)).svg(
            stream,
            scale=5,
            xmldecl=False,
            svgns=False,
            module_color='#2c3d2d'
        )
        qrcode = stream.getvalue().decode('utf-8')

        return render_template(
            'onboarding_pairing.html',
            qrcode=qrcode,
            pincode=bridge_state.pincode.decode()
        )

    return None

# @http.route("/config", methods=['GET'])
# def config():
#
#     res = {}
#
#     return render_template(
#         'onboarding_devices.html',
#         entities=res
#     )


def xhm_uri(pincode, setup_id):
    """
    Generates the X-HM:// uri (Setup Code URI)

    :rtype: str
    """
    payload = 0
    payload |= 0 & 0x7  # version

    payload <<= 4
    payload |= 0 & 0xF  # reserved bits

    payload <<= 8
    payload |= 2 & 0xFF  # category

    payload <<= 4
    payload |= 2 & 0xF  # flags

    payload <<= 27
    payload |= (
            int(pincode.replace(b"-", b""), 10) & 0x7FFFFFFF
    )  # pincode

    encoded_payload = base36.dumps(payload).upper()
    encoded_payload = encoded_payload.rjust(9, "0")

    return "X-HM://" + encoded_payload + setup_id


def run_server():
    """
    Starting the flask server
    """
    serve(http, host="0.0.0.0", port=8081)
