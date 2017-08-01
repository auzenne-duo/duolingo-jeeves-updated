function getParameterByName(name, defaultValue) {
  var url = window.location.href;
  name = name.replace(/[\[\]]/g, '\\$&');
  var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
  var results = regex.exec(url);
  if (!results) return defaultValue;
  if (!results[2]) return defaultValue;
  return decodeURIComponent(results[2].replace(/\+/g, ' '));
}
