from io import BytesIO

import base36
from flask import Flask, render_template, redirect, request
from pyqrcode import QRCode
from waitress import serve

from .. import config
from ..helper import write_config

http = Flask(__name__)
http.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
http.config['TEMPLATES_AUTO_RELOAD'] = True
http.jinja_env.auto_reload = True


@http.route("/")
def main():

    c = config.read_config_file()
    if 'token' not in c:
        return redirect("/onboarding/start", code=302)
    else:
        from ..digitalstrom import state_collector
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


@http.route("/homekit/state")
def homekit_state():
    from ..homekit import homekit
    state = homekit.bridge_state()

    return str(state.paired)


@http.route("/save-devices", methods=['POST'])
def save_devices():
    from ..digitalstrom import device_collector

    request_data = request.get_json()

    devices = request_data['devices']
    devices_subapplication = request_data['device_subapplication']

    entities = device_collector.get_entities()

    device_obj = []
    for device in devices:
        d = ({v['entity_id']: v for v in entities}).get(device)
        if devices_subapplication.get(device):
            d['service'] = devices_subapplication.get(device)
        device_obj.append(d)

    zoneids = list(set([i['zoneid'] for i in device_obj if 'zoneid' in i]))

    zone_obj = []
    for zoneid in zoneids:
        zone_devices = device_collector.get_zone(zoneid)['devices']
        z = {
            "id": zoneid,
            "applications": zone_devices
        }
        zone_obj.append(z)

    from ..helper import write_config
    write_config(config.args.config_path + '/config.yml', {'entities': device_obj, 'zones': zone_obj})
    restart_bridge()
    return {"ok": True}


@http.route("/api/requesttoken", methods=['GET', 'POST'])
def requesttoken():
    from ..digitalstrom.helper import create_application_token

    response = None
    if request.method == 'POST':
        """modify/update the information for <user_id>"""
        password = request.form.get('password')
        response = create_application_token(password)

    if response['ok']:
        data = {"token": response['token']}
        write_config(config.args.config_path + '/config.yml', data)

    return response


@http.route("/restart-bridge", methods=['POST'])
def restart_bridge():
    from ..homekit import start_homekit, stop_homekit
    import time
    stop_homekit()
    time.sleep(2.4)
    start_homekit()

    return {"success": True}


@http.route("/onboarding/<step>", methods=['GET'])
def onboarding(step):
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
        from ..digitalstrom import device_collector

        from ..helper import read_config
        entities = device_collector.get_entities()
        cur_config = read_config(config.args.config_path + '/config.yml')
        print(entities)
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
        from ..homekit import homekit
        bridge_state = homekit.bridge_state()
        stream = BytesIO()
        QRCode(xhm_uri(bridge_state.pincode, bridge_state.setup_id)).svg(
            stream,
            scale=5,
            xmldecl=False,
            svgns=False,
            module_color='#2c3d2d'
        )
        qr = stream.getvalue().decode('utf-8')

        return render_template(
            'onboarding_pairing.html',
            qrcode=qr,
            pincode=bridge_state.pincode.decode()
        )


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
    """Generates the X-HM:// uri (Setup Code URI)

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
    serve(http, host="0.0.0.0", port=8081)
