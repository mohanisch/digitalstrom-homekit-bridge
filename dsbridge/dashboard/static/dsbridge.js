$(document).ready(function () {
    var checkedDevices = {
        devices: [],
        device_subapplication: {}
    };

    $.each($('input.entityid'), function() {
        if ($(this).is(':checked') == true) {
            var entityid = $(this).data('entityid')
            checkedDevices.devices.push(entityid);
        }
    });
    console.log(checkedDevices)

    $('input.entityid').on('change', function(e){
        var entityid = $(this).data('entityid')

        if ($(this).is(':checked')) {
            if(checkedDevices.devices.indexOf(entityid) === -1) {
                checkedDevices.devices.push(entityid);
                console.log(checkedDevices)
            }
        }
        else {
            if(checkedDevices.devices.indexOf(entityid) !== -1) {
                checkedDevices.devices.splice(checkedDevices.devices.indexOf(entityid), 1);
                console.log(checkedDevices)
            }
        }
    });
    $('select.subapplication').on('change', function(e){
        var sub_app = $(this).find(':selected').data('subapplication')
        var sub_entityid = $(this).data('entityid')
        var object = {[sub_entityid]: sub_app}

        checkedDevices.device_subapplication[sub_entityid] = sub_app
        console.log(checkedDevices)
    });


    $(function($) {
        $( document ).bind( "enhance", function(){
            $( "body" ).addClass( "enhanced" );
        });

        $( document ).trigger( "enhance" );
    });
    $('input#save-devices').click( function() {
        $('#main-mid').waitMe({
            effect : 'rotateplane',
            text : 'Konfiguration wird gespeichert...',
            bg : 'rgba(255,255,255,0.7)',
            color : '#000'
        });
        $("body").scrollTop(0);

        $.ajax({
            url: "/save-devices",
            type: 'post',
            dataType: 'json',
            data: JSON.stringify(checkedDevices),
            contentType: 'application/json',
            success: function(result) {
                console.log("return: "  + result);
                if(result['ok']) {
                    setTimeout(function(){ window.location.href='/onboarding/pairing'; }, 3000);
                }
            }
        });
    });
});