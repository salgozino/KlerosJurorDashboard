import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    console.log('Loading court table, please wait')
    $.ajax({
        url: '/_getAdoption',
        data: {"network": network},
        type: 'GET',
        success: function(response, network){
            console.log(response)
            $('#adoptionValue').html('<h4>'+response+'</h4>');
        },
        error: function(error){
            console.log(error);
            $('#adoptionValue').html('Eror loading adoption');
        }
    });
});
