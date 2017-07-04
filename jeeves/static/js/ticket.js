function loadTickets(page, word) {
    var params = {page: page};
    if (word) {
        params['word'] = word;
    }
    $.get('/api/1/tickets', params).done(function(response) {
        var tickets = response.data;
        var next_url = response.next_url;
        var content = '';
        for (var i in tickets) {
            var ticket = tickets[i];
            var category_html = '';
            for (var category_name in ticket.category_labels) {
                category_html += `<div class="category_wrapper">
                                  <input type="checkbox" id="${category_name}_${i}">&nbsp;
                                  <label for="${category_name}_${i}">${category_name}</label>
                                  </div>`;
            }
            ticket.description = ticket.description.replace(/\n/g, '<br>');
            if (word) {
              ticket.description = ticket.description.replace(RegExp('(' + word + ')', 'g'), '<mark>$1</mark>');
            }
            content += `<table><tr>
            <th width="150">ID</td>
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
            <tr>
            <th>Category labels</td>
            <td>${category_html}</td>
            </tr>
            </table>
            <br>`;
        }
        var paramString = '?' + (word ? 'word=' + word + '&' : '') + 'page=' + (page + 1);
        window.history.pushState(null, null, window.location.pathname + paramString);
        $('.next').data('next_page', page + 1);
        $('html, body').animate({ scrollTop: 0 });
        $('#tickets').html(content);
    });
}
