from io import BytesIO

import base36
from flask import Flask, render_template, redirect, request
from pyqrcode import QRCode
from waitress import serve

from dsHomekit import config
from dsHomekit.helper import write_config

http = Flask(__name__)
http.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
http.config['TEMPLATES_AUTO_RELOAD'] = True
http.jinja_env.auto_reload = True


# homekit_state = homekit.bridge_state()


@http.route("/")
def main():
    c = config.read_config_file()
    if 'token' not in c:
        return redirect("/onboarding/start", code=302)
    else:
        from ..digitalstrom.device_collector import DssCollector
        entities = DssCollector().get_entities()
        res = {}
        for item in entities:
            res.setdefault(item['zone'], []).append(item)

        return render_template(
            'dashboard_main.html',
            entities=entities
        )


@http.route("/homekit/state")
def homekit():
    from dsHomekit.homekit import homekit
    state = homekit.bridge_state()

    return str(state.paired)

@http.route("/save-devices", methods=['GET', 'POST'])
def save_devices():
    import yaml

    data = {"devices": {"include": request.form.getlist('devices')}}

    from ..utils.helper import write_config
    write_config(config.args.config_path + '/config.yml', data)

    return {"ok": True}


@http.route("/api/requesttoken", methods=['GET', 'POST'])
def requesttoken():
    from ..digitalstrom.helper import create_application_token
    response = None
    if request.method == 'POST':
        """modify/update the information for <user_id>"""
        password = request.form.get('password')
        response = create_application_token(password)
        print(response)

    if response['ok']:
        data = {"token": response['token']}
        write_config(config.args.config_path + '/config.yml', data)

    return response


@http.route("/onboarding/", methods=['GET'])
def test():
    return redirect("/onboarding/start", code=302)


@http.route("/onboarding/<step>", methods=['GET'])
def onboarding(step):
    dstoken = False
    initial_config = False
    paired = False

    #if homekit_state.paired:
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
        from ..digitalstrom.device_collector import DssCollector
        entities = DssCollector().get_entities(filter=False)

        res = {}
        for item in entities:
            res.setdefault(item['zone'], []).append(item)

        return render_template(
            'onboarding_devices.html',
            entities=res  # json.dumps(b)
        )
    if step == 'pairing':
        from dsHomekit.homekit import homekit
        homekit_state = homekit.bridge_state()
        stream = BytesIO()
        QRCode(xhm_uri(homekit_state.pincode, homekit_state.setup_id)).svg(
            stream,
            scale=5,
            xmldecl=False,
            svgns=False,
            module_color='#2c3d2d'
        )
        qr = stream.getvalue().decode('utf-8')
        del homekit

        return render_template(
            'onboarding_pairing.html',
            qrcode=qr,
            pincode=homekit_state.pincode.decode()
        )


def run_server():
    serve(http, host="0.0.0.0", port=8081)


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
