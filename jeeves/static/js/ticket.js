$(document).ready(function() {
    loadTickets(0);
});

function loadTickets(page) {
    $.get('/api/1/tickets', {page: page}).done(function(response) {
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
        window.history.pushState(null, null, '/training/'+(page + 1));
        $('.next').data('next_page', page + 1);
        $('html, body').animate({ scrollTop: 0 });
        $('#tickets').html(content);
    });
    }
