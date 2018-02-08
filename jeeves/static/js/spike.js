function renderSpikes(jQueryElement, limit) {
  $.get('/api/1/spikes', function(data) {
    var keys = [];
    for (var key in data) {
      keys[keys.length] = key;
    }
    keys.sort();
    keys = keys.reverse();
    var html = '';
    for (var i = 0; i < keys.length; i++) {
      if (typeof limit !== 'undefined' && limit <= i) {
        break;
      }
      var key = keys[i];
      html += `<h3>${key}</h3>`;
      var score_word_pairs = data[key]['spike'];
      var result = '';
      for (var j = 0; j < score_word_pairs.length; j++) {
        var score = score_word_pairs[j][0];
        var word = score_word_pairs[j][1];
        result += `<tr>
                     <td>${score.toFixed(1)}</td>
                     <td><a href="/analysis?word=${word}">${word}</a></td>
                     </tr>`;
        if (typeof limit !== 'undefined' && j == 4) {
          break;
        }
      }
      if (result) {
        result = `<table>
                    <tr><th class="score_header">Spikiness</th><th>Spiked Word</th></tr>
                    ${result}
                    </table>`;
      } else {
        result = 'No spikes found.';
      }
      html += result;
    }
    jQueryElement.html(html);
  });
}
