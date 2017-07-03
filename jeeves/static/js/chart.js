function drawChart() {
  var data = new google.visualization.DataTable();
  data.addColumn('date', 'X');
  data.addColumn('number', 'Zendesk tickets');
  var JAN_FIRST = new Date('2017-01-01');
  var keyword = $('#query').val();
  $.get('/api/1/time_series', {word: keyword}).done(function(response) {
      var pairs = [];
      for (var dateString in response.values) {
          if (new Date(dateString) < JAN_FIRST) {
              continue;
          }
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
      window.history.pushState(null, null, '/analysis?word=' + keyword);
  });

}
