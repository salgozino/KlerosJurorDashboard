import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    if (network == null ) network = 'mainnet'
    $.ajax({
        url: '/_getUSDThroughCourt/'+courtID,
        data: {"network": network},
        type: 'GET',
        success: function(response){
            var formatter = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
              });
            $('#feesUSD').html('<h4>'+formatter.format(response)+'</h4>');
        },
        error: function(error){
            console.log(error);
            $('#feesUSD').html('Eror loading data');
        }
    });
});
