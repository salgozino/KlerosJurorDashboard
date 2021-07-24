import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    if (network == null ) network = 'mainnet'
    $.ajax({
        url: '/_getProfileNetReward/'+address,
        data: {"network": network},
        type: 'GET',
        success: function(response){
            var formatter = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
              });
            $('#netUSD').html('<h4>'+formatter.format(response)+'</h4>');
        },
        error: function(error){
            console.log(error);
            $('#netUSD').html('Eror loading data');
        }
    });
});
