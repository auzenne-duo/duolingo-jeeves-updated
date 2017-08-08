function loadTickets(page, word, start_time, end_time) {
  page = parseInt(page);
  var params = { page: page };
  if (word) {
    params.word = word;
    if (word === '') {
      return;
    }
  }
  if (start_time) {
    params.start_time = start_time;
  }
  if (end_time) {
    params.end_time = end_time;
  }

  params.meta_filter = getParameterByName('meta_filter', '');
  var showCategory = !word;
  $.get('/api/1/tickets', params).done(function(response) {
    var tickets = response.data;
    var next_url = response.next_url;
    var content = '';
    for (var i in tickets) {
      var ticket = tickets[i];
      var category_html = '';
      if (showCategory) {
        for (var category_name in ticket.category_labels) {
          var checked = ticket.category_labels[category_name] ? 'checked' : '';
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
      ticket.description = ticket.description
        .trim()
        .replace(/\n{3,}/g, '\n\n')
        .replace(/\n/g, '<br>');
      if (word) {
        ticket.description = ticket.description.replace(
          RegExp('\\b(' + word + ')\\b', 'gi'),
          '<mark>$1</mark>'
        );
      }
      content += `<table class="ticket_table" data-id="${ticket.ticket_id}"><tr>
            <th>ID</td>
            <td>
            <a href="https://duolingotest.zendesk.com/agent/tickets/${ticket.ticket_id}"
               target="_blank">${ticket.ticket_id}</a>
            </td>
            </tr>
            <tr>
            <th>Date</td>
            <td>${ticket.date_time}</td>
            </tr>
            <tr>
            <th>Subject</td>
            <td>${ticket.subject}</td>
            </tr>
            <tr>
            <th>Description</td>
            <td>
            ${ticket.description}
            </td>
            </tr>
            ${category_html}
            </table>
            <br>`;
    }
    let state = getJsonFromUrl();
    if (word) {
      state['word'] = word;
    } else {
      delete state['word'];
    }
    state['page'] = page;
    var paramString = JsonToQueryString(state);
    const path = window.location.pathname + paramString;
    window.history.pushState(null, null, path);
    if (!start_time && !end_time) {
      // Avoid loadTickets() triggered by modifyRange() to count as pageview.
      ga('send', 'pageview', path);
    }

    $('.next').data('next_page', page + 1);
    $('html, body').animate({ scrollTop: 0 });
    $('#tickets').html(content);

    $('input').click(function(e) {
      $(e.target).closest('table').data('updated', true);
    });
  });
}
