import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    if (network == null ) network = 'mainnet'
    $.ajax({
        url: '/_getMostActiveCourt',
        data: {"network": network},
        type: 'GET',
        success: function(response, network){
            console.log(response)
            var htmlText = '<h4>'
            if (response){
                htmlText += response
            } else {
                htmlText += 'No activity in last days'
            }
            htmlText += '</h4>'
            $('#mostActiveValue').html(htmlText);
        },
        error: function(error){
            console.log(error);
            $('#mostActiveValue').html('Eror loading data');
        }
    });
});
