async function fetchJson(url, opts) {
  var res = await fetch(url, opts || {});
  if (!res.ok) {
    var text = await res.text();
    throw new Error('HTTP ' + res.status + ' ' + res.statusText + '\n' + text);
  }
  return await res.json();
}
