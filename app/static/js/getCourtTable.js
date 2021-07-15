import {getUrlParameter} from './getUrlParameter.js'

$(function(){
    var network = getUrlParameter('network')
    $.ajax({
        url: '/_getCourtTable',
        data: {"network": network},
        type: 'GET',
        success: function(response, network){
            var formatter = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
              });

            // BODY
            var tableHTML = '';
            var mostActiveID = 0;
            $.each(response, function () {
                if (this['Disputes in the last 30 days'] > mostActiveID){
                    mostActiveID = this.id
                }
            });
            $.each(response, function () {
                if (this.id == mostActiveID){
                    console.log()
                    tableHTML +='<tr class="success">';
                } else {
                    tableHTML += '<tr>'
                }
                tableHTML += '<th scope="row"><a href="/court?id="'+this.id+'&network='+network+'">'+this.Name+'</a></th>'
                        +'<td class="text-right">'+this.id+'</td>'
                        +'<td class="text-right">'+this['Total Staked'].toLocaleString()+'</td>'
                        +'<td class="text-right">'+this.Jurors+'</td>'
                        +'<td class="text-right">'+this['Fee For Juror'].toFixed(0)+'</td>'
                        +'<td class="text-right">'+this['Min Stake'].toFixed(2)+'</td>'
                        +'<td class="text-right">'+formatter.format(this['Min Stake in USD'])+'</td>'
                        +'<td class="text-right">'+this['Vote Stake'].toFixed(0)+'</td>'
                        +'<td class="text-right">'+this['Total Disputes']+'</td>'
                        +'<td class="text-right">'+this['Disputes in the last 30 days']+'</td>'
                        +'<td class="text-right">'+this['Open Disputes']+'</td>'
                        +'</tr>';
            });
            $('#courtTableBody').html(tableHTML);

        },
        error: function(error){
            console.log(error);
            $('#courtTableBody').html('<tr><td>Error loading the table, please refresh the site</td></tr>');
        }
    });
});
