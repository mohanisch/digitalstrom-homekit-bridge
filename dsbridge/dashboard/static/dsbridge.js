$(document).ready(function () {
    var checkedDevices = {
        devices: [],
        device_subapplication: {}
    };

    // Initialize checked devices and subapplications from page load
    $.each($('input.entityid'), function() {
        if ($(this).is(':checked') == true) {
            var entityid = $(this).data('entityid')
            checkedDevices.devices.push(entityid);

            // Also initialize subapplication if select exists and has a selected value
            var $select = $('select.subapplication[data-entityid="' + entityid + '"]');
            if ($select.length > 0) {
                var selectedOption = $select.find(':selected');
                if (selectedOption.length > 0) {
                    var sub_app = selectedOption.data('subapplication');
                    if (sub_app) {
                        checkedDevices.device_subapplication[entityid] = sub_app;
                    }
                }
            }
        }
    });
    console.log('Initialized checkedDevices:', checkedDevices)

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
                    $('#main-mid').waitMe('hide');
                    // Show success message and redirect to dashboard
                    alert('Konfiguration erfolgreich gespeichert!');
                    setTimeout(function(){ window.location.href='/'; }, 500);
                } else {
                    $('#main-mid').waitMe('hide');
                    alert('Fehler beim Speichern: ' + (result.error || 'Unbekannter Fehler'));
                }
            },
            error: function(xhr) {
                $('#main-mid').waitMe('hide');
                var errorMsg = 'Fehler beim Speichern';
                try {
                    var result = JSON.parse(xhr.responseText);
                    errorMsg = result.error || errorMsg;
                } catch(e) {}
                alert(errorMsg);
            }
        });
    });
});