var JAN_FIRST = new Date('2017-01-01');

var currier = function(fn) {
  var args = Array.prototype.slice.call(arguments, 1);

  return function() {
    return fn.apply(this, args.concat(
      Array.prototype.slice.call(arguments, 0)));
  };
};

function modifyRange(keyword, eventdata={}){
  // now, we must grab new tickets based on the new range
  var xstart = eventdata['xaxis.range[0]'];
  var xend = eventdata['xaxis.range[1]'];

  xstart = (xstart === undefined) ? null : xstart;
  xend = (xend === undefined) ? null : xend;
  if (xstart && xend) {
    ga('send', 'event', {
      eventCategory: 'Tickets',
      eventAction: 'modify_range'
    });
  }
  loadTickets(0, keyword, xstart, xend);
  $('.next').prop('onclick', null).off('click').click(function() {
    loadTickets($(this).data('next_page'), keyword, xstart, xend);
  });
}

function drawChart() {
  var keyword = $('#query').val();
  $.get('/api/1/time_series', {word: keyword}).done(function(response) {
    var datetimes = Object.keys(response.values).filter(k => new Date(k) >= JAN_FIRST);
    var freqs = datetimes.map(dt => response.values[dt]);
    var trace = {
      type: 'scatter',
      mode: 'lines',
      x: datetimes,
      y: freqs,
      hovertext: 'Zendesk tickets',
      line: {
        color: '#3E82F7'
      }
    };

    var layout = {
      title: '# of tickets containing "<b>' + keyword + '</b>"',
      titlefont: {
        size: 22,
        color: '#999999'
      },
      font: {
        family: 'museo-sans-rounded, sans-serif'
      },
      showlegend: false,
      xaxis: {
        title: 'Date',
        showgrid: 'false'
      },
      yaxis: {
        title: '# of tickets',
        fixedrange: true,
        gridcolor: '#efefef'
      },
      margin: {
        l: 50,
        r: 0,
        b: 50,
        t: 75,
        pad: 4
      }
    };

    var config = {
      showLink: false,
      displayModeBar: false
    };

    Plotly.newPlot('chart_container', [trace], layout, config);
    modifyRange(keyword);
    var chart = document.getElementById('chart_container');
    chart.on('plotly_relayout', currier(modifyRange, keyword));
    window.history.pushState(null, null, '/analysis?word=' + keyword);
    ga('send', 'event', {
      eventCategory: 'Tickets',
      eventAction: 'search',
      eventLabel: keyword
    });
  });

}
