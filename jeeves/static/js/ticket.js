$(document).ready(function() {
$.get('/api/1/tickets').done(function(tickets) {
    var content = '';
    for (var i in tickets) {
        var ticket = tickets[i];
        var category_html = '';
        for (var category_name in ticket.category_labels) {
            category_html += `<span class="category_wrapper"><input type="checkbox">${category_name}</span>`;
        }
        ticket.description = ticket.description.replace(/\n/g, '<br>');
        content += `<table><tr>
        <th width="150">ID</td>
        <td><a href="#">${ticket.ticket_id}</a></td>
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
    $('#tickets').html(content);
});
});
