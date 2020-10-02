var ORIGIN = new Date();
ORIGIN.setDate(ORIGIN.getDate() - 100);

var currier = function(fn) {
  var args = Array.prototype.slice.call(arguments, 1);

  return function() {
    return fn.apply(
      this,
      args.concat(Array.prototype.slice.call(arguments, 0))
    );
  };
};

function eventManager(lang, fieldname, eventdata) {
  let state = getJsonFromUrl();
  keyword = state["word"];
  let col = eventdata.points[0].x;
  let meta_filter = JSON.parse(getParameterByName("meta_filter", "{}"));
  meta_filter[fieldname] = col;
  state.meta_filter = JSON.stringify(meta_filter);

  window.history.pushState(
    null,
    null,
    "/" + lang + "/analysis" + JsonToQueryString(state)
  );

  ga("send", "event", {
    eventCategory: "Metadata",
    eventAction: "metadata_filter",
  });

  drawChart(lang, true);
}

function modifyRange(lang, keyword, eventdata = {}) {
  // now, we must grab new tickets based on the new range
  var xstart;
  var xend;
  if (jQuery.isEmptyObject(eventdata)) {
    [xstart, xend] = $("#chart_container")[0].layout.xaxis.range;
  } else {
    xstart = eventdata["xaxis.range[0]"];
    xend = eventdata["xaxis.range[1]"];

    xstart = xstart === undefined || xstart === "" ? null : xstart;
    xend = xend === undefined || xstart === "" ? null : xend;
  }

  if (xstart && xend) {
    ga("send", "event", {
      eventCategory: "Tickets",
      eventAction: "modify_range",
    });
  }
  let score_function = getParameterByName("score", "");
  let meta_filter_str = getParameterByName("meta_filter", "");
  loadTickets(lang, 0, keyword, xstart, xend);
  $(".next")
    .prop("onclick", null)
    .off("click")
    .click(function() {
      loadTickets(lang, $(this).data("next_page"), keyword, xstart, xend);
    });
}

function drawChart(lang, updateData) {
  var keyword = $("#query").val();
  let meta_filter_str = getParameterByName("meta_filter", "");
  $.get("/api/1/" + lang + "/time_series", {
    word: keyword,
    meta_filter: meta_filter_str,
  }).done(function(response) {
    var datetimes = Object.keys(response.values).filter(
      k => new Date(k) >= ORIGIN
    );
    var freqs = datetimes.map(dt => response.values[dt]);
    var trace = {
      type: "scatter",
      mode: "lines",
      x: datetimes,
      y: freqs,
      hovertext: "Zendesk tickets",
      line: {
        color: "#3E82F7",
      },
    };

    var layout = {
      title: '# of tickets containing "<b>' + keyword + '</b>"',
      titlefont: {
        size: 22,
        color: "#999999",
      },
      font: {
        family: "museo-sans-rounded, sans-serif",
      },
      showlegend: false,
      xaxis: {
        title: "Date",
        showgrid: "false",
      },
      yaxis: {
        title: "# of tickets",
        fixedrange: true,
        gridcolor: "#efefef",
        rangemode: "tozero",
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

    if (updateData === undefined) {
      Plotly.newPlot("chart_container", [trace], layout, config);
    } else {
      Plotly.update("chart_container", { x: [trace.x], y: [trace.y] });
    }
    modifyRange(lang, keyword);
    var chart = document.getElementById("chart_container");
    chart.on("plotly_relayout", currier(modifyRange, lang, keyword));
    let state = getJsonFromUrl();
    state["word"] = keyword;
    window.history.pushState(
      null,
      null,
      "/" + lang + "/analysis" + JsonToQueryString(state)
    );
    ga("send", "event", {
      eventCategory: "Tickets",
      eventAction: "search",
      eventLabel: keyword,
    });
  });
}
