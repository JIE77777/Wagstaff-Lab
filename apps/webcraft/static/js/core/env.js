var APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/, '');
var api = function (path) {
  return APP_ROOT + path;
};
