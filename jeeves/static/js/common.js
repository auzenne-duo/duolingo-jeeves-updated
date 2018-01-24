function getParameterByName(name, defaultValue) {
  var url = window.location.href;
  name = name.replace(/[\[\]]/g, '\\$&');
  var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
  var results = regex.exec(url);
  if (!results) return defaultValue;
  if (!results[2]) return defaultValue;
  return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function getJsonFromUrl(hashBased) {
  var query;
  if (hashBased) {
    var pos = location.href.indexOf('?');
    if (pos == -1) return [];
    query = location.href.substr(pos + 1);
  } else {
    query = location.search.substr(1);
  }
  var result = {};
  query.split('&').forEach(function(part) {
    if (!part) return;
    part = part.split('+').join(' '); // replace every + with space, regexp-free version
    var eq = part.indexOf('=');
    var key = eq > -1 ? part.substr(0, eq) : part;
    var val = eq > -1 ? decodeURIComponent(part.substr(eq + 1)) : '';
    var from = key.indexOf('[');
    if (from == -1) result[decodeURIComponent(key)] = val;
    else {
      var to = key.indexOf(']', from);
      var index = decodeURIComponent(key.substring(from + 1, to));
      key = decodeURIComponent(key.substring(0, from));
      if (!result[key]) result[key] = [];
      if (!index) result[key].push(val);
      else result[key][index] = val;
    }
  });
  return result;
}

function JsonToQueryString(j) {
  return '?' + Object.keys(j).map(key => `${key}=${j[key]}`).join('&');
}

function dateToYMD(date) {
    var d = date.getDate();
    var m = date.getMonth() + 1; //Month from 0 to 11
    var y = date.getFullYear();
    return '' + y + '-' + (m<=9 ? '0' + m : m) + '-' + (d <= 9 ? '0' + d : d);
}
