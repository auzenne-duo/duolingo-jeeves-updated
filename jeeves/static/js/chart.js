google.charts.load('current', {packages: ['corechart', 'line']});
google.charts.setOnLoadCallback(drawChart);


function drawChart() {
  var data = new google.visualization.DataTable();
  data.addColumn('date', 'X');
  data.addColumn('number', 'Zendesk tickets');
  var keyword = $('#query').val()
  $.get('/api/1/time_series', {word: keyword, debug: DEBUG ? '1' : ''}).done(function(response) {
      var pairs = [];
      for (var dateString in response.values) {
          pairs.push([new Date(dateString), response.values[dateString]])
      }
      data.addRows(pairs);

      var options = {
        title: '# of tickets containing "' + keyword + '"',
        vAxis: {
          title: '#'
        },
        colors: ['#3E82F7'],
        legend: {position: 'none'},
        hAxis: {
          gridlines: {
            color: 'transparent'
          },
          format: 'yyyy-MM-dd'
        },
        vAxis: {
          gridlines: {
            color: '#efefef'
          }
        },
        titleTextStyle: {
          color: '#999999',
          fontSize: 22,
        }
      };

      var chart = new google.visualization.LineChart(document.getElementById('chart_container'));
      chart.draw(data, options);
      window.history.pushState(null, null, '/analysis?word=' + keyword + (DEBUG ? '&debug=1' : ''));
  });

}
