var JAN_FIRST = new Date('2017-01-01');

var currier = function(fn) {
  var args = Array.prototype.slice.call(arguments, 1);

  return function() {
    return fn.apply(
      this,
      args.concat(Array.prototype.slice.call(arguments, 0))
    );
  };
};

function modifyRange(keyword, eventdata = {}) {
  // now, we must grab new tickets based on the new range
  var xstart = eventdata['xaxis.range[0]'];
  var xend = eventdata['xaxis.range[1]'];

  xstart = xstart === undefined || xstart === '' ? null : xstart;
  xend = xend === undefined || xstart === '' ? null : xend;
  if (xstart && xend) {
    ga('send', 'event', {
      eventCategory: 'Tickets',
      eventAction: 'modify_range',
    });
  }
  let score_function = getParameterByName('score', '');
  $.get('/api/1/metadata_analyze', {word: keyword, start_time: xstart, end_time: xend, score: score_function}).done(function(response) {
    $('#metadata-container').empty();
    let len = response.metadata.length;
    for (var i = 0; i < len; i++) {
      let {field: field, score: score} = response.metadata[i];
      let container_id = `metadata_${field}`;
      // $(`<div id=${container_id} class="metadata_plot" />`).appendTo('metadata-container');
      $('#metadata-container').append(`<div id=${container_id} class="metadata_plot"></div>`);
      let word_dist = response.word[field];
      let wordless_dist = response.wordless[field];
      let word_meta_cat_names = Object.keys(word_dist);
      let word_freqs = word_meta_cat_names.map(name => word_dist[name]);

      let wordless_meta_cat_names = Object.keys(wordless_dist);
      let wordless_freqs = wordless_meta_cat_names.map(name => wordless_dist[name]);

      var constrained_trace = {
        type: 'bar',
        name: `Word-constrained ${field}`,
        // mode: 'bar',
        x: word_meta_cat_names,
        y: word_freqs,
        hovertext: 'Keyword-matching tickets',
        marker: {
          color: 'rgb(49,130,189)'
        },
        xaxis: 'x',
        yaxis: 'y',
      };

      var full_trace = {
        type: 'bar',
        name: `Wordless ${field}`,
        // mode: 'bar',
        x: wordless_meta_cat_names,
        y: wordless_freqs,
        hovertext: 'All tickets',
        marker: {
          color: 'rgb(204,204,204)'
        },
        xaxis: 'x',
        yaxis: 'y',
      };
      var layout = {
        barmode: 'group',
        title: `Distribution over ${field}`,
        titlefont: {
          size: 22,
          color: '#999999'
        },
        font: {
          family: 'museo-sans-rounded, sans-serif'
        },
        showlegend: true,
        xaxis: {
          title: field,
          fixedrange: true,
          showgrid: 'false',
          type: 'category',
        },
        yaxis: {
          title: 'Fraction of Tickets',
          fixedrange: true,
          gridcolor: 'rgb(49,130,189)'
        },
        // yaxis2: {
        //   title: 'Full # of tickets',
        //   fixedrange: true,
        //   gridcolor: 'rgb(204,204,204)',
        //   side: 'right'
        // },
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

      let data = [constrained_trace, full_trace];

      Plotly.newPlot(container_id, data, layout, config);
      }
  });

  loadTickets(0, keyword, xstart, xend);
  $('.next').prop('onclick', null).off('click').click(function() {
    loadTickets($(this).data('next_page'), keyword, xstart, xend);
  });
}

function drawChart() {
  var keyword = $('#query').val();
  $.get('/api/1/time_series', { word: keyword }).done(function(response) {
    var datetimes = Object.keys(response.values).filter(
      k => new Date(k) >= JAN_FIRST
    );
    var freqs = datetimes.map(dt => response.values[dt]);
    var trace = {
      type: 'scatter',
      mode: 'lines',
      x: datetimes,
      y: freqs,
      hovertext: 'Zendesk tickets',
      line: {
        color: '#3E82F7',
      },
    };

    var layout = {
      title: '# of tickets containing "<b>' + keyword + '</b>"',
      titlefont: {
        size: 22,
        color: '#999999',
      },
      font: {
        family: 'museo-sans-rounded, sans-serif',
      },
      showlegend: false,
      xaxis: {
        title: 'Date',
        showgrid: 'false',
      },
      yaxis: {
        title: '# of tickets',
        fixedrange: true,
        gridcolor: '#efefef',
      },
      margin: {
        l: 50,
        r: 0,
        b: 50,
        t: 75,
        pad: 4,
      },
    };

    var config = {
      showLink: false,
      displayModeBar: false,
    };

    Plotly.newPlot('chart_container', [trace], layout, config);
    modifyRange(keyword);
    var chart = document.getElementById('chart_container');
    chart.on('plotly_relayout', currier(modifyRange, keyword));
    window.history.pushState(null, null, `/analysis?word=${keyword}`);
    ga('send', 'event', {
      eventCategory: 'Tickets',
      eventAction: 'search',
      eventLabel: keyword,
    });
  });
}
