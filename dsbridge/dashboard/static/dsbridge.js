$(document).ready(function () {
    var checkedDevices = {
        devices: [],
        device_subapplication: {}
    };

    $('input.entityid').on('change', function(e){
        var entityid = $(this).data('entityid')

        if ($(this).is(':checked')) {
            if(checkedDevices.devices.indexOf(entityid) === -1) {
                checkedDevices.devices.push(entityid);
            }
        }
        else {
            if(checkedDevices.devices.indexOf(entityid) !== -1) {
                checkedDevices.devices.splice(checkedDevices.devices.indexOf(entityid), 1);
            }
        }
    });
    $('select.subapplication').on('change', function(e){
        var sub_app = $(this).find(':selected').data('subapplication')
        var sub_entityid = $(this).data('entityid')
        var object = {[sub_entityid]: sub_app}

        checkedDevices.device_subapplication[sub_entityid] = sub_app
    });


    $(function($) {
        $( document ).bind( "enhance", function(){
            $( "body" ).addClass( "enhanced" );
        });

        $( document ).trigger( "enhance" );
    });
    $('input#save-devices').click( function() {
        $.ajax({
            url: "/save-devices",
            type: 'post',
            dataType: 'json',
            data: JSON.stringify(checkedDevices),
            contentType: 'application/json',
            success: function(result) {
            console.log("return: "  + result);
                if(result['ok']) {
                   $('#main-mid').waitMe({
                        effect : 'rotateplane',
                        text : 'Konfiguration wird gespeichert...',
                        bg : 'rgba(255,255,255,0.7)',
                        color : '#000'
                    });
                    //setTimeout(function(){ window.location.href='/onboarding/pairing'; }, 3000);
                }
            }
        });
    });
});