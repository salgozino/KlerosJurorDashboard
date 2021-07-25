import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    if (network == null ) network = 'mainnet'

    $.ajax({
        url: "/_getAllStakes",
        type: "GET",
        datatype: 'json',
        data: {"network": network},
        success: function (data) {
            $('#stakesTable').DataTable({
                data: data,  // Get the data object
                columns: [
                    { 'data': 'timestamp', "render": function(data){
                        return new Date(data * 1000).toUTCString();
                    } },
                    { 'data': 'address', "render": function ( data, type, row, meta ) {
                        return '<a href="profile/'+data+'?network='+network+'">'+data+'</a>';
                      }},
                    { 'data': 'subcourtID', "render": function ( data, type, row, meta ) {
                        return '<a href="court/?id='+data+'&network='+network+'">'+data+'</a>';
                      } },
                    { 'data': 'stake', render: $.fn.dataTable.render.number( ',', '.', 0 ) },
                    { 'data': 'newTotalStake', render: $.fn.dataTable.render.number( ',', '.', 0 )  },
                    { 'data': 'id' },
                ],
                "pageLength": 50,
                "columnDefs": [
                    { "visible": false, "targets":  5}
                  ]
            });
        },
        error: function(error){
            console.log(error);
            $('#stakesTable').html('Eror loading data');
        }
    });
});