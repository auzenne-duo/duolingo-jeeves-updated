function loadTickets(lang, page, word, start_time, end_time) {
  page = parseInt(page);
  var params = { page: page };
  if (word) {
    params.word = word;
    if (word === "") {
      return;
    }
  }
  if (start_time) {
    params.start_time = start_time;
  }
  if (end_time) {
    params.end_time = end_time;
  }

  params.meta_filter = getParameterByName("meta_filter", "");
  var showCategory = !word;
  $.get("/api/1/" + lang + "/tickets", params).done(function(response) {
    var tickets = response.data;
    var next_url = response.next_url;
    var content = "";
    for (var i in tickets) {
      var ticket = tickets[i];
      var category_html = "";
      if (showCategory) {
        for (var category_name in ticket.category_labels) {
          var checked = ticket.category_labels[category_name] ? "checked" : "";
          category_html += `<div>
                                      <input type="checkbox" id="${category_name}_${i}" value="${category_name}" ${checked}>&nbsp;
                                      <label for="${category_name}_${i}">${category_name}</label>
                                      </div>`;
        }
        if (category_html) {
          category_html = `<tr>
                                     <th>Categories</th>
                                     <td>${category_html}</td>
                                     </tr>`;
        }
      }
      ticket.body_text = ticket.body_text
        .trim()
        .replace(/\n{3,}/g, "\n\n")
        .replace(/\n/g, "<br>");
      if (word) {
        ticket.body_text = ticket.body_text.replace(
          RegExp("\\b(" + word + ")\\b", "gi"),
          "<mark>$1</mark>"
        );
      }
      var source = "";
      var tags = "";
      var tags_text = "";
      if (`${ticket.data_source}` == "Zendesk") {
        if (ticket.via.source && ticket.via.source.from) {
          if (ticket.via.source.from.name) {
            source += `${ticket.via.source.from.name}`;
          }
          if (ticket.via.source.from.address) {
            source += `  &lt;${ticket.via.source.from.address}&gt;`;
          }
        }
        source += ` via ${ticket.via.channel}`;
        tags =
          ticket.priority !== null
            ? `<span class="p0-tag">${ticket.priority}</span> `
            : "";
        tags += ticket.tags
          .map(function(tag) {
            return `<span class="p1-tag">${tag}</span>`;
          })
          .join(" ");
        tags_text = `<tr><th>Tags</th><td>${tags}</td></tr>`;
      }
      var zd_ticket_anchor_open = "";
      var zd_user_anchor_open = "";
      var zd_anchor_close = "";
      if (`${ticket.data_source}` == "Zendesk") {
        zd_ticket_anchor_open = `<a href="${ticket.links[0]}" target="_blank">`;
        zd_user_anchor_open = `<a href="${ticket.links[1]}" target="_blank">`;
        zd_anchor_close = "</a>";
      }

      var data_source_display_name = ticket.data_source;
      if (ticket.data_source == "AppFigures") {
        data_source_display_name += ", ";
        data_source_display_name += ticket.store;
      }

      content += `<table class="ticket_table" data-id="${ticket.ticket_id}">
            <tr>
              <th>Subject</th>
              <td>${ticket.header_text}</td>
            </tr>
            <tr>
              <th>Date</th>
              <td>${zd_ticket_anchor_open}${utcToLocal(
        ticket.date_time
      )}${zd_anchor_close}
              </td>
            </tr>
            <tr>
              <th>Source</th>
              <td>${zd_user_anchor_open}${source} ${data_source_display_name}${zd_anchor_close}
              </td>
            </tr>
            ${tags_text}
            <tr>
              <th>Description</th>
              <td>
              ${ticket.body_text}
              </td>
            </tr>
            ${category_html}
            </table>
            <br>`;
    }
    let state = getJsonFromUrl();
    if (word) {
      state["word"] = word;
    } else {
      delete state["word"];
    }
    state["page"] = page;
    var paramString = JsonToQueryString(state);
    const path = window.location.pathname + paramString;
    window.history.pushState(null, null, path);
    if (!start_time && !end_time) {
      // Avoid loadTickets() triggered by modifyRange() to count as pageview.
      ga("send", "pageview", path);
    }

    $(".next").data("next_page", page + 1);
    $("html, body").animate({
      scrollTop: page && page >= 1 ? $("#ticket_list").offset().top - 100 : 0,
    });
    $("#tickets").html(content);

    $("input").click(function(e) {
      $(e.target)
        .closest("table")
        .data("updated", true);
    });
  });
}
