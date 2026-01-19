(function () {
  var meta = document.querySelector('meta[name="app-root"]');
  var root = meta ? meta.content : '';
  root = String(root || '').replace(/\/+$/, '');

  var base = root + '/static/app/js/';
  var page = (document.body && document.body.dataset) ? (document.body.dataset.page || '') : '';
  var pageMap = {
    craft: ['pages/craft.js'],
    catalog: ['pages/catalog.js'],
    cooking: function () {
      var role = (document.body && document.body.dataset) ? (document.body.dataset.role || '') : '';
      var items = ['pages/cooking_shared.js'];
      if (role === 'tool') items.push('pages/cooking_tool.js');
      else items.push('pages/cooking_encyclopedia.js');
      return items;
    },
  };

  var scripts = [
    'core/env.js',
    'core/dom.js',
    'core/api.js',
  ];
  if (pageMap[page]) {
    var entry = pageMap[page];
    if (typeof entry === 'function') entry = entry();
    if (Array.isArray(entry)) scripts = scripts.concat(entry);
    else scripts.push(entry);
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
