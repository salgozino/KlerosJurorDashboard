import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    if (network == null ) network = 'mainnet'
    $.ajax({
        url: '/_getRetention',
        data: {"network": network},
        type: 'GET',
        success: function(response, network){
            $('#retentionValue').html('<h4>'+parseFloat(response*100).toFixed(2)+'%</h4>');
        },
        error: function(error){
            console.log(error);
            $('#retentionValue').html('Eror loading data');
        }
    });
});
