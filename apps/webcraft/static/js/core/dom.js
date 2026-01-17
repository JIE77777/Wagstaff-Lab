function el(id) {
  return document.getElementById(id);
}

function escHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, function (c) {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[c];
  });
}
