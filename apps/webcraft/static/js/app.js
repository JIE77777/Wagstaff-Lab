(function () {
  var meta = document.querySelector('meta[name="app-root"]');
  var root = meta ? meta.content : '';
  root = String(root || '').replace(/\/+$/, '');

  var base = root + '/static/app/js/';
  var page = (document.body && document.body.dataset) ? (document.body.dataset.page || '') : '';
  var pageMap = {
    craft: 'pages/craft.js',
    catalog: 'pages/catalog.js',
    cooking: 'pages/cooking.js',
  };

  var scripts = [
    'core/env.js',
    'core/dom.js',
    'core/api.js',
  ];
  if (pageMap[page]) {
    scripts.push(pageMap[page]);
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var node = document.createElement('script');
      node.src = base + src;
      node.async = false;
      node.onload = resolve;
      node.onerror = function () {
        reject(new Error('Failed to load ' + src));
      };
      document.head.appendChild(node);
    });
  }

  function chain(idx) {
    if (idx >= scripts.length) return;
    loadScript(scripts[idx])
      .then(function () { chain(idx + 1); })
      .catch(function (err) { console.error(err); });
  }

  chain(0);
})();
